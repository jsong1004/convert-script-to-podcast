import re
from youtube_transcript_api import YouTubeTranscriptApi
import google.generativeai as genai
# Add imports for video/audio processing
import tempfile
from moviepy.editor import VideoFileClip
import speech_recognition as sr
import os
from pydub import AudioSegment

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

def summarize_with_gemini(transcript, api_key, preferred_language='en'):
    """Summarize transcript using Google's Gemini model in the preferred language."""
    try:
        # Configure the Gemini API
        genai.configure(api_key=api_key)
        
        # Get model name from environment or default
        model_name = os.getenv('GOOGLE_MODEL', 'gemini-pro')
        # Set up the model
        model = genai.GenerativeModel(model_name)
        
        # Language instruction (use language codes as keys)
        language_instruction = {
            'en': 'Generate the summary in English.',
            'ko': 'Generate the summary in Korean. 모든 요약 결과를 한국어로 출력하세요.',
            'es': 'Genera el resumen en español.',
            'fr': 'Générez le résumé en français.',
            'de': 'Erstellen Sie die Zusammenfassung auf Deutsch.',
            'it': 'Genera il riassunto in italiano.',
            'pt': 'Gere o resumo em português.',
            'ru': 'Сделайте резюме на русском языке.',
            'ja': '要約を日本語で生成してください。',
            'zh': '请用中文生成摘要。'
        }.get(preferred_language, 'Generate the summary in English.')
        
        # Generate a summary
        prompt = f"""Please provide a comprehensive summary of the following transcript. 
        Focus on the main topics, key points, and important details.
        {language_instruction}
        
        Transcript:
        {transcript[:30000]}  # Limit to avoid token limits
        """
        
        response = model.generate_content(prompt)
        return response.text
    
    except Exception as e:
        raise Exception(f"Error generating summary: {str(e)}")

def transcribe_video_file(video_file_path, language="en-US"):
    """
    Extract audio from a video file and transcribe it to text using speech_recognition.
    Handles long files by chunking audio into 60-second segments.
    Returns the transcript as a string.
    """
    recognizer = sr.Recognizer()
    transcript = ""
    temp_audio_path = None
    try:
        # Extract audio from video using moviepy
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_audio:
            temp_audio_path = temp_audio.name
        video = VideoFileClip(video_file_path)
        video.audio.write_audiofile(temp_audio_path, codec='pcm_s16le')
        video.close()

        # Chunked transcription
        audio = AudioSegment.from_wav(temp_audio_path)
        chunk_length_ms = 60 * 1000  # 60 seconds
        chunks = [audio[i:i+chunk_length_ms] for i in range(0, len(audio), chunk_length_ms)]
        
        for i, chunk in enumerate(chunks):
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as chunk_file:
                chunk.export(chunk_file.name, format='wav')
                chunk_path = chunk_file.name
            try:
                with sr.AudioFile(chunk_path) as source:
                    audio_data = recognizer.record(source)
                    try:
                        chunk_transcript = recognizer.recognize_google(audio_data, language=language)
                        transcript += chunk_transcript + " "
                    except sr.UnknownValueError:
                        transcript += "[Unintelligible audio] "
                    except sr.RequestError as e:
                        transcript += f"[Recognition error: {e}] "
            finally:
                if os.path.exists(chunk_path):
                    os.remove(chunk_path)
        return transcript.strip()
    except Exception as e:
        raise Exception(f"Error transcribing video file: {str(e)}")
    finally:
        if temp_audio_path and os.path.exists(temp_audio_path):
            os.remove(temp_audio_path) 