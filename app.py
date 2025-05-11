import os
from flask import Flask, render_template, request, send_from_directory, jsonify, url_for, redirect
from dotenv import load_dotenv
from murf import Murf
from pydub import AudioSegment
import uuid
import requests
import io
import logging
import google.generativeai as genai # For Google Gemini
from pptx import Presentation # For reading .pptx files
import PyPDF2 # For reading PDF files
from blog_generator import BlogGenerator
from youtube_transcript import extract_video_id, get_transcript, summarize_with_gemini
from audio_transcript import extract_transcript, get_supported_languages
from google.cloud import storage

# Import Blueprints
from presentation_converter import presentation_bp
from podcast_generator import podcast_bp

load_dotenv()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'output_audio'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB upload limit

# Register blueprints
app.register_blueprint(podcast_bp)
app.register_blueprint(presentation_bp)

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Load API keys (Blueprints will load them via os.getenv as well, or could access via app.config)
MURFA_API_KEY = os.getenv("MURFA_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not MURFA_API_KEY:
    print("Error: MURFA_API_KEY not found in .env file.") # Or use app.logger if app is initialized
if not GOOGLE_API_KEY:
    print("Error: GOOGLE_API_KEY not found in .env file.") # Or use app.logger
else:
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        # app.logger will be available after app initialization for logging this
        # For now, print or basic log before app context is fully up for blueprints
        print("Google Gemini API configured successfully.")
    except Exception as e:
        print(f"Failed to configure Google Gemini API: {e}")

GCS_BUCKET_NAME = 'startup_consulting'

def upload_to_gcs(local_file_path, destination_blob_name):
    storage_client = storage.Client()
    bucket = storage_client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(local_file_path)
    return blob.public_url

def generate_gcs_signed_url(blob_name, expiration=3600):
    storage_client = storage.Client()
    bucket = storage_client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(blob_name)
    url = blob.generate_signed_url(expiration=expiration)
    return url

# --- Helper functions for Presentation Converter ---
def extract_text_from_pptx(pptx_file_stream):
    """Extracts all text from a .pptx file stream."""
    try:
        prs = Presentation(pptx_file_stream)
        text_runs = []
        for slide in prs.slides:
            for shape in slide.shapes:
                if not shape.has_text_frame:
                    continue
                for paragraph in shape.text_frame.paragraphs:
                    for run in paragraph.runs:
                        text_runs.append(run.text)
        return "\n".join(text_runs)
    except Exception as e:
        app.logger.error(f"Error extracting text from PPTX: {e}")
        raise ValueError(f"Could not extract text from presentation: {e}")

def extract_text_from_pdf(pdf_file_stream):
    """Extracts all text from a PDF file stream."""
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file_stream)
        text = []
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            text.append(page.extract_text())
        return "\n".join(text)
    except Exception as e:
        app.logger.error(f"Error extracting text from PDF: {e}")
        raise ValueError(f"Could not extract text from PDF: {e}")

def generate_script_with_gemini(presentation_text, script_style):
    """Generates script using Google Gemini API."""
    if not GOOGLE_API_KEY:
        raise ValueError("Google API Key is not configured.")

    model_name = "gemini-1.5-pro-latest" # Or "gemini-pro" if 1.5 is not available/needed
    try:
        model = genai.GenerativeModel(model_name)
    except Exception as e:
        app.logger.error(f"Error initializing Gemini model '{model_name}': {e}")
        # Fallback or specific model selection logic can be added here
        # For example, try "gemini-pro" if "gemini-1.5-pro-latest" fails
        try:
            model_name = "gemini-pro" # A common fallback
            model = genai.GenerativeModel(model_name)
            app.logger.info(f"Successfully initialized fallback Gemini model: {model_name}")
        except Exception as fallback_e:
            app.logger.error(f"Error initializing fallback Gemini model '{model_name}': {fallback_e}")
            raise ValueError(f"Could not initialize Gemini model. Please check API key and model availability. Error: {fallback_e}")


    common_prompt_instructions = (
        "You are an expert scriptwriter. Convert the following presentation slide content into a spoken script. "
        "The script should be very detailed for each slide concept. "
        "The tone should be passionate, knowledgeable, and educational, like someone speaking engagingly in front of many people. "
        "Include easy-to-understand examples where appropriate to clarify concepts. "
        "Do not include any titles, subtitles, or descriptive slide markers like 'Slide 1 of 5' or 'Next slide'. "
        "Only output the text that will be spoken. Ensure smooth transitions between ideas if they were on different slides."
    )

    if script_style == "podcast":
        style_specific_instructions = (
            "The script should be in a podcast format with multiple voices. "
            "Use 'HOST:' for the main narrator and overall flow. "
            "Use 'VOICE 1:', 'VOICE 2:', etc., for different perspectives, examples, or to break up longer segments of HOST narration. "
            "Ensure a conversational and engaging flow between speakers. The HOST should guide the conversation."
        )
    elif script_style == "speech":
        style_specific_instructions = (
            "The script should be for a single speaker. All text should be attributed to 'HOST:'. "
            "Ensure a continuous, engaging monologue suitable for a keynote presentation."
        )
    else:
        raise ValueError("Invalid script style selected.")

    full_prompt = f"{common_prompt_instructions}\n\n{style_specific_instructions}\n\nPRESENTATION CONTENT:\n---\n{presentation_text}\n---\n\nGENERATED SCRIPT:"

    try:
        app.logger.info(f"Sending request to Gemini with model {model_name}. Prompt length: {len(full_prompt)}")
        response = model.generate_content(full_prompt)
        # Check for safety ratings or blocks if necessary, depending on Gemini version and response structure
        if hasattr(response, 'prompt_feedback') and response.prompt_feedback.block_reason:
            app.logger.error(f"Gemini content generation blocked. Reason: {response.prompt_feedback.block_reason}")
            app.logger.error(f"Block details: {response.prompt_feedback.safety_ratings}")
            raise ValueError(f"Content generation blocked by safety filters. Reason: {response.prompt_feedback.block_reason}")

        if not response.parts:
             app.logger.warning(f"Gemini response has no parts. Full response: {response}")
             # Try to access text directly if parts is empty but text attribute exists
             if hasattr(response, 'text') and response.text:
                 return response.text.strip()
             raise ValueError("Received an empty response from Gemini.")
        
        # Assuming the first part contains the text, or iterate if multiple parts
        generated_text = "".join(part.text for part in response.parts if hasattr(part, 'text'))
        if not generated_text.strip():
            app.logger.warning(f"Gemini generated empty text. Full response: {response}")
            raise ValueError("Gemini generated an empty script.")
            
        app.logger.info("Successfully received script from Gemini.")
        return generated_text.strip()

    except Exception as e:
        app.logger.error(f"Error calling Google Gemini API: {e}", exc_info=True)
        # Check for specific API errors if the SDK provides them
        if "API key not valid" in str(e) or "PERMISSION_DENIED" in str(e):
             raise ValueError("Google Gemini API Key is invalid or lacks permissions. Please check your .env file and Google Cloud project settings.")
        raise ValueError(f"Failed to generate script using Gemini: {e}")

# --- End of Presentation Converter helpers ---

def parse_script(script_text):
    """Parses the input script into a list of dictionaries.
    Each dictionary: {'speaker': 'HOST'/'Voice X', 'text': '...'}
    Example input:
    HOST: Hello world!
    Voice 1: This is a test.
    """
    lines = script_text.strip().split('\n')
    parsed_script = []
    for line in lines:
        line = line.strip()
        if ':' in line:
            parts = line.split(':', 1)
            speaker = parts[0].strip()
            text = parts[1].strip()
            if speaker and text: # Ensure both speaker and text are present
                parsed_script.append({'speaker': speaker, 'text': text})
        elif line: # Handle lines without a speaker, perhaps assign to a default or skip
            # For now, let's assume lines without ':' are continuations or to be ignored
            # Or, assign to a default speaker if that's the desired behavior
            # For this implementation, we'll only process lines with "speaker: text" format
            app.logger.info(f"Skipping line without speaker: {line}")
            pass 
    return parsed_script

def get_voice_config(speaker_name):
    """Returns (voice_id) for a given speaker.
    Voice styles can also be added here if needed by Murf AI.
    Refer to Murf AI documentation for available voice_ids.
    These are examples, replace with actual desired voice_ids.
    """
    speaker_name_upper = speaker_name.upper()
    # Example voice IDs (replace with actual valid voice IDs from Murf AI)
    # Trying 'en-US-natalie' for HOST as 'en-US-ryan' resulted in a 502 error in logs.
    if speaker_name_upper == "HOST":
        return "en-US-ryan" # Changed back to a common default, ensure this is valid for your account
    elif speaker_name_upper == "VOICE 1":
        return "en-US-natalie"    # Example voice ID, ensure this is valid
    elif speaker_name_upper == "VOICE 2":
        return "en-US-natalie"    # Example voice ID, ensure this is valid
    else:
        # Default voice if speaker not recognized
        app.logger.warning(f"Speaker '{speaker_name}' not recognized, using default voice.")
        return "en-US-natalie" # Default fallback voice, ensure this is valid

# --- End of helper functions ---

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/convert_podcast', methods=['GET', 'POST'])
def convert_podcast():
    if request.method == 'POST':
        script_text_from_area = request.form.get('script')
        script_file = request.files.get('script_file')
        final_script_text = ""

        if script_file and script_file.filename != '':
            try:
                if script_file.content_type.startswith('text/'):
                    final_script_text = script_file.read().decode('utf-8')
                    app.logger.info(f"Successfully read script from uploaded file: {script_file.filename}")
                else:
                    return render_template('convert_podcast.html', error="Invalid file type. Please upload a text file (e.g., .txt, .md).", script_text=script_text_from_area)
            except Exception as e:
                app.logger.error(f"Error reading uploaded file: {e}")
                return render_template('convert_podcast.html', error=f"Error reading uploaded file: {str(e)}", script_text=script_text_from_area)
        elif script_text_from_area:
            final_script_text = script_text_from_area
        else:
            return render_template('convert_podcast.html', error="Script text or a script file is required.")

        if not final_script_text.strip():
             return render_template('convert_podcast.html', error="Script content is empty.", script_text=script_text_from_area)

        if not MURFA_API_KEY:
            return render_template('convert_podcast.html', error="Murf AI API Key is not configured. Please contact the administrator.", script_text=final_script_text)

        try:
            app.logger.info("Starting audio generation process.")
            parsed_script = parse_script(final_script_text)
            if not parsed_script:
                return render_template('convert_podcast.html', error="Could not parse the script. Ensure it follows 'SPEAKER: Text' format or the file content is valid.", script_text=final_script_text)

            audio_segments = []
            murf_client = Murf(api_key=MURFA_API_KEY)
            app.logger.info(f"Parsed script: {parsed_script}")

            for i, item in enumerate(parsed_script):
                app.logger.info(f"Processing segment {i+1}/{len(parsed_script)}: Speaker: {item['speaker']}, Text: {item['text'][:30]}...")
                voice_id = get_voice_config(item['speaker'])
                
                app.logger.info(f"Generating audio for: '{item['text']}' with voice '{voice_id}'")
                
                tts_response = murf_client.text_to_speech.generate(
                    text=item['text'],
                    voice_id=voice_id
                )
                
                audio_url = tts_response.audio_file # This is a URL
                app.logger.info(f"Audio URL received from Murf SDK: {audio_url}")

                # Download the audio from the URL
                audio_download_response = requests.get(audio_url)
                audio_download_response.raise_for_status() # Ensure the request was successful
                
                # Load audio data into Pydub from bytes.
                file_extension = audio_url.split('?')[0].split('.')[-1].lower()
                if file_extension not in ['mp3', 'wav', 'ogg', 'flv', 'aac']:
                    app.logger.warning(f"Unexpected audio file extension '{file_extension}' from Murf, attempting to load as wav.")
                    file_extension = "wav"

                segment_audio = AudioSegment.from_file(io.BytesIO(audio_download_response.content), format=file_extension)
                audio_segments.append(segment_audio)
                app.logger.info(f"Segment {i+1} processed and added from URL.")

            if not audio_segments:
                return render_template('convert_podcast.html', error="No audio segments were generated. Check script and API logs.", script_text=final_script_text)

            # Combine audio segments
            app.logger.info("Combining audio segments...")
            combined_audio = AudioSegment.empty()
            for segment in audio_segments:
                combined_audio += segment
            
            # Generate a unique filename for the final output
            unique_filename = f"final_audio_{uuid.uuid4().hex}.mp3"
            output_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            
            app.logger.info(f"Exporting combined audio to {output_path}")
            combined_audio.export(output_path, format="mp3")

            gcs_blob_name = f"audio/{unique_filename}"
            gcs_url = upload_to_gcs(output_path, gcs_blob_name)
            if os.path.exists(output_path):
                os.remove(output_path)

            app.logger.info("Audio generation successful.")
            return render_template('convert_podcast.html', audio_file_url=gcs_url, script_text=final_script_text)

        except requests.exceptions.HTTPError as http_err:
            app.logger.error(f"HTTP error during Murf API audio download: {http_err}")
            app.logger.error(f"Response content: {http_err.response.content if http_err.response else 'No response content'}")
            return render_template('convert_podcast.html', error=f"An HTTP error occurred while downloading audio from Murf: {http_err}", script_text=final_script_text)
        except Murf.ApiError as murf_api_err:
            app.logger.error(f"Murf API Error: Status {murf_api_err.status_code}, Body: {murf_api_err.body}", exc_info=True)
            error_message = f"Murf API Error (Status {murf_api_err.status_code}). "
            if murf_api_err.status_code == 502:
                error_message += "This might be a temporary issue with the Murf AI service (Bad Gateway). Please try again shortly or check the voice ID and text segment."
            else:
                error_message += "Please check your script, API key, and Murf AI account status."
            return render_template('convert_podcast.html', error=error_message, script_text=final_script_text)
        except Exception as e:
            app.logger.error(f"Error during audio generation: {e}", exc_info=True)
            return render_template('convert_podcast.html', error=f"An unexpected error occurred: {str(e)}", script_text=final_script_text)

    return render_template('convert_podcast.html')

@app.route('/convert_presentation', methods=['GET', 'POST'])
def convert_presentation():
    if request.method == 'POST':
        presentation_file = request.files.get('presentation_file')
        script_style = request.form.get('script_style')
        
        if not presentation_file or presentation_file.filename == '':
            return render_template('convert_presentation.html', error="No presentation file selected.")
        
        if not script_style:
            return render_template('convert_presentation.html', error="No script style selected.")

        allowed_extensions = {'pptx', 'pdf'}
        file_ext = presentation_file.filename.rsplit('.', 1)[1].lower() if '.' in presentation_file.filename else ''
        
        if file_ext not in allowed_extensions:
            return render_template('convert_presentation.html', error="Invalid file type. Please upload a .pptx or .pdf file.")

        try:
            app.logger.info(f"Processing presentation file: {presentation_file.filename}, style: {script_style}")
            # Read file into a stream to pass to pptx.Presentation or PDF parser
            file_stream = io.BytesIO(presentation_file.read())
            
            if file_ext == 'pptx':
                presentation_text = extract_text_from_pptx(file_stream)
            elif file_ext == 'pdf':
                presentation_text = extract_text_from_pdf(file_stream)
            
            if not presentation_text.strip():
                return render_template('convert_presentation.html', error="Could not extract any text from the presentation, or the presentation is empty.")

            app.logger.info(f"Extracted text length: {len(presentation_text)}")
            
            generated_script = generate_script_with_gemini(presentation_text, script_style)
            
            return render_template('convert_presentation.html', generated_script=generated_script)

        except ValueError as ve: # Catch custom ValueErrors for better user feedback
            app.logger.error(f"ValueError during presentation conversion: {ve}")
            return render_template('convert_presentation.html', error=str(ve))
        except Exception as e:
            app.logger.error(f"Unexpected error during presentation conversion: {e}", exc_info=True)
            return render_template('convert_presentation.html', error=f"An unexpected error occurred: {str(e)}")

    return render_template('convert_presentation.html')

@app.route('/convert_to_blog', methods=['GET', 'POST'])
def convert_to_blog():
    if request.method == 'POST':
        script_text = request.form.get('script')
        script_file = request.files.get('script_file')
        blog_style = request.form.get('blog_style', 'informative')
        final_script_text = script_text or ''

        if script_file and script_file.filename != '':
            try:
                if script_file.content_type.startswith('text/') or script_file.filename.endswith(('.txt', '.md')):
                    final_script_text = script_file.read().decode('utf-8')
                else:
                    return render_template('convert_to_blog.html', error="Invalid file type. Please upload a text file (e.g., .txt, .md).", script_text=script_text)
            except Exception as e:
                app.logger.error(f"Error reading uploaded file: {e}")
                return render_template('convert_to_blog.html', error=f"Error reading uploaded file: {str(e)}", script_text=script_text)

        if not final_script_text.strip():
            return render_template('convert_to_blog.html', error="Script text or a script file is required.", script_text=script_text)
        if not GOOGLE_API_KEY:
            return render_template('convert_to_blog.html', error="Google API Key is not configured.", script_text=final_script_text)
        try:
            blog_generator = BlogGenerator(GOOGLE_API_KEY)
            blog_data = blog_generator.generate_blog_post(final_script_text, blog_style)
            if not os.path.exists('output_blog'):
                os.makedirs('output_blog')
            blog_filename = f"blog_{uuid.uuid4()}.html"
            blog_path = os.path.join('output_blog', blog_filename)
            with open(blog_path, 'w', encoding='utf-8') as f:
                f.write(blog_generator.format_html(blog_data))
            gcs_blog_blob = f"blog/{blog_filename}"
            gcs_blog_url = upload_to_gcs(blog_path, gcs_blog_blob)
            if os.path.exists(blog_path):
                os.remove(blog_path)
            return render_template('convert_to_blog.html', generated_blog=blog_data['content'], script_text=final_script_text, blog_file_url=gcs_blog_url)
        except Exception as e:
            app.logger.error(f"Error generating blog post: {e}")
            return render_template('convert_to_blog.html', 
                                 error=f"Error generating blog post: {str(e)}",
                                 script_text=final_script_text)
    return render_template('convert_to_blog.html')

@app.route('/download_blog')
def download_blog():
    try:
        # Get the most recently generated blog post in GCS
        storage_client = storage.Client()
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blobs = list(bucket.list_blobs(prefix='blog/'))
        if not blobs:
            return "No blog posts available for download.", 404
        latest_blob = max(blobs, key=lambda b: b.time_created)
        signed_url = generate_gcs_signed_url(latest_blob.name)
        return redirect(signed_url)
    except Exception as e:
        app.logger.error(f"Error downloading blog post: {e}")
        return str(e), 500

@app.route('/download/<filename>')
def download_file(filename):
    try:
        blob_name = f"audio/{filename}"
        signed_url = generate_gcs_signed_url(blob_name)
        return redirect(signed_url)
    except Exception as e:
        app.logger.error(f"Error generating signed URL for audio: {e}")
        return str(e), 500

@app.route('/youtube_transcript', methods=['GET', 'POST'])
def youtube_transcript():
    if request.method == 'POST':
        youtube_url = request.form.get('youtube_url')
        language = request.form.get('language', 'en')
        
        if not youtube_url:
            return render_template('youtube_transcript.html', error="Please provide a YouTube URL.")
        
        try:
            video_id = extract_video_id(youtube_url)
            if not video_id:
                return render_template('youtube_transcript.html', error="Invalid YouTube URL.")
            
            transcript = get_transcript(video_id, language)
            if not transcript:
                return render_template('youtube_transcript.html', error="Could not generate transcript.")
            
            # Generate summary using Gemini
            if GOOGLE_API_KEY:
                try:
                    summary = summarize_with_gemini(transcript, GOOGLE_API_KEY)
                except Exception as e:
                    app.logger.error(f"Error generating summary: {e}")
                    summary = None
            else:
                summary = None
            
            return render_template('youtube_transcript.html', 
                                 transcript=transcript,
                                 summary=summary)
            
        except Exception as e:
            app.logger.error(f"Error processing YouTube transcript: {e}")
            return render_template('youtube_transcript.html', error=str(e))
    
    return render_template('youtube_transcript.html')

@app.route('/audio_transcript', methods=['GET', 'POST'])
def audio_transcript():
    if request.method == 'POST':
        if 'audio_file' not in request.files:
            return render_template('audio_transcript.html', 
                                 error="No audio file provided.",
                                 languages=get_supported_languages())
        
        audio_file = request.files['audio_file']
        language = request.form.get('language', 'en-US')
        
        if audio_file.filename == '':
            return render_template('audio_transcript.html', 
                                 error="No audio file selected.",
                                 languages=get_supported_languages())
        
        try:
            # Save the uploaded file temporarily
            temp_file = os.path.join(app.config['UPLOAD_FOLDER'], f"temp_{uuid.uuid4().hex}")
            audio_file.save(temp_file)
            
            # Extract transcript
            transcript = extract_transcript(temp_file, language)
            
            # Clean up temporary file
            if os.path.exists(temp_file):
                os.unlink(temp_file)
            
            return render_template('audio_transcript.html', 
                                 transcript=transcript,
                                 languages=get_supported_languages())
            
        except Exception as e:
            app.logger.error(f"Error processing audio file: {e}")
            # Clean up temporary file if it exists
            if os.path.exists(temp_file):
                os.unlink(temp_file)
            return render_template('audio_transcript.html', 
                                 error=str(e),
                                 languages=get_supported_languages())
    
    return render_template('audio_transcript.html', languages=get_supported_languages())

if __name__ == '__main__':
    # Basic logging configuration
    # Flask's app.logger will use this configuration once the app is running
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    # Log API key status using app.logger after app is created
    with app.app_context():
        if GOOGLE_API_KEY:
            app.logger.info("Google Gemini API key loaded.")
        else:
            app.logger.error("Google Gemini API key NOT loaded.")
        if MURFA_API_KEY:
            app.logger.info("Murf AI API key loaded.")
        else:
            app.logger.error("Murf AI API key NOT loaded.")
    app.run(debug=True)