import re
from youtube_transcript_api import YouTubeTranscriptApi
import google.generativeai as genai

def extract_video_id(url):
    """Extract YouTube video ID from URL."""
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([\w-]+)',  # Standard YouTube URLs
        r'(?:youtube\.com\/embed\/)([\w-]+)',                # Embed URLs
        r'(?:youtube\.com\/v\/)([\w-]+)',                    # Direct video URLs
        r'(?:youtube\.com\/shorts\/)([\w-]+)',               # YouTube Shorts
        r'(?:youtube\.com\/live\/)([\w-]+)'                  # YouTube Livestreams
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None

def get_transcript(video_id, language="en"):
    """Get transcript from YouTube video."""
    try:
        # First try to get the transcript in the requested language
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=[language])
            transcript_source = f"Original {language} transcript"
        except:
            # If that fails, list available languages
            available_transcripts = YouTubeTranscriptApi.list_transcripts(video_id)
            
            # Try to find a translatable transcript
            available_languages = []
            
            for transcript in available_transcripts:
                lang_code = transcript.language_code
                lang_name = transcript.language
                is_translatable = transcript.is_translatable
                available_languages.append((lang_code, lang_name, is_translatable, transcript))
            
            # If no translatable transcript is available,
            # use the first available transcript in its original language
            if available_languages:
                selected_lang_code = available_languages[0][0]
                selected_transcript = available_languages[0][3]
                
                transcript_list = selected_transcript.fetch()
                transcript_source = f"Original {selected_lang_code} transcript"
            else:
                raise Exception("No transcripts available for this video.")
        
        # Concatenate all transcript segments
        full_transcript = ""
        for segment in transcript_list:
            if isinstance(segment, dict) and "text" in segment:
                full_transcript += segment["text"] + " "
            else:
                try:
                    if hasattr(segment, "text"):
                        full_transcript += segment.text + " "
                    elif hasattr(segment, "__dict__"):
                        full_transcript += str(segment.__dict__) + " "
                    else:
                        full_transcript += str(segment) + " "
                except:
                    continue
        
        # Add a note about the transcript source
        full_transcript = f"# Transcript Source: {transcript_source}\n\n" + full_transcript
        
        return full_transcript
    
    except Exception as e:
        raise Exception(f"Error extracting transcript: {str(e)}")

def summarize_with_gemini(transcript, api_key):
    """Summarize transcript using Google's Gemini model."""
    try:
        # Configure the Gemini API
        genai.configure(api_key=api_key)
        
        # Set up the model
        model = genai.GenerativeModel('gemini-pro')
        
        # Generate a summary
        prompt = f"""Please provide a comprehensive summary of the following transcript. 
        Focus on the main topics, key points, and important details.
        
        Transcript:
        {transcript[:30000]}  # Limit to avoid token limits
        """
        
        response = model.generate_content(prompt)
        return response.text
    
    except Exception as e:
        raise Exception(f"Error generating summary: {str(e)}") 