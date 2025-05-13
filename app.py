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
from youtube_transcript import extract_video_id, get_transcript, summarize_with_gemini, transcribe_video_file
from audio_transcript import extract_transcript, get_supported_languages
from google.cloud import storage

# Import Blueprints
from presentation_converter import presentation_bp
from podcast_generator import podcast_bp, get_voice_config, detect_language

load_dotenv()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'output_audio'
app.config['MAX_CONTENT_LENGTH'] = 1000 * 1024 * 1024  # 100 MB upload limit

# Register blueprints
app.register_blueprint(podcast_bp)
app.register_blueprint(presentation_bp)

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Load API keys (Blueprints will load them via os.getenv as well, or could access via app.config)
MURFA_API_KEY = os.getenv("MURFA_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_MODEL = os.getenv("GOOGLE_MODEL", "gemini-2.0-flash")

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

GCS_BUCKET_NAME = 'startup-consulting'

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
# REMOVE extract_text_from_pptx, extract_text_from_pdf, generate_script_with_gemini (presentation conversion helpers)

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

# --- End of helper functions ---

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/convert_podcast', methods=['GET', 'POST'])
def convert_podcast():
    script_text_from_area = ""
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
            return render_template('convert_podcast.html', error="Script text or a script file is required.", script_text=script_text_from_area)

        if not final_script_text.strip():
             return render_template('convert_podcast.html', error="Script content is empty.", script_text=script_text_from_area)

        if not MURFA_API_KEY:
            return render_template('convert_podcast.html', error="Murf AI API Key is not configured. Please contact the administrator.", script_text=final_script_text)

        try:
            app.logger.info("Starting audio generation process.")
            parsed_script = parse_script(final_script_text)
            if not parsed_script:
                return render_template('convert_podcast.html', error="Could not parse the script. Ensure it follows 'SPEAKER: Text' format or the file content is valid.", script_text=final_script_text)

            # Detect language from the first non-empty text segment
            output_language = 'en'  # default
            for item in parsed_script:
                if item['text'].strip():
                    output_language = detect_language(item['text'])
                    app.logger.info(f"Detected language: {output_language}")
                    break

            audio_segments = []
            murf_client = Murf(api_key=MURFA_API_KEY)
            app.logger.info(f"Parsed script: {parsed_script}")

            for i, item in enumerate(parsed_script):
                app.logger.info(f"Processing segment {i+1}/{len(parsed_script)}: Speaker: {item['speaker']}, Text: {item['text'][:30]}...")
                voice_id = get_voice_config(item['speaker'], output_language=output_language)
                app.logger.info(f"Generating audio for: '{item['text']}' with voice '{voice_id}'")
                tts_response = murf_client.text_to_speech.generate(
                    text=item['text'],
                    voice_id=voice_id
                )
                audio_url = tts_response.audio_file
                app.logger.info(f"Audio URL received from Murf SDK: {audio_url}")
                audio_download_response = requests.get(audio_url)
                audio_download_response.raise_for_status()
                file_extension = audio_url.split('?')[0].split('.')[-1].lower()
                if file_extension not in ['mp3', 'wav', 'ogg', 'flv', 'aac']:
                    app.logger.warning(f"Unexpected audio file extension '{file_extension}' from Murf, attempting to load as wav.")
                    file_extension = "wav"
                segment_audio = AudioSegment.from_file(io.BytesIO(audio_download_response.content), format=file_extension)
                audio_segments.append(segment_audio)
                app.logger.info(f"Segment {i+1} processed and added from URL.")

            if not audio_segments:
                return render_template('convert_podcast.html', error="No audio segments were generated. Check script and API logs.", script_text=final_script_text)

            app.logger.info("Combining audio segments...")
            combined_audio = AudioSegment.empty()
            for segment in audio_segments:
                combined_audio += segment
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

    return render_template('convert_podcast.html', script_text=script_text_from_area)

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
        video_file = request.files.get('video_file')
        transcript = None
        summary = None
        error = None
        
        try:
            if video_file and video_file.filename != '':
                # Handle uploaded video file
                import tempfile
                from youtube_transcript import transcribe_video_file, summarize_with_gemini
                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(video_file.filename)[-1]) as temp_video:
                    video_file.save(temp_video.name)
                    temp_video_path = temp_video.name
                try:
                    # Use language code for speech_recognition (e.g., 'en-US', 'ko-KR')
                    lang_map = {
                        'en': 'en-US', 'ko': 'ko-KR'
                    }
                    sr_language = lang_map.get(language, 'en-US')
                    app.logger.info(f"Transcribing video file with language: {sr_language}")
                    transcript = transcribe_video_file(temp_video_path, language=sr_language)
                finally:
                    if os.path.exists(temp_video_path):
                        os.remove(temp_video_path)
                if GOOGLE_API_KEY:
                    summary = summarize_with_gemini(transcript, GOOGLE_API_KEY, preferred_language=language)
            elif youtube_url:
                # Handle YouTube URL as before
                from youtube_transcript import extract_video_id, get_transcript, summarize_with_gemini
                video_id = extract_video_id(youtube_url)
                if not video_id:
                    error = "Invalid YouTube URL."
                else:
                    transcript = get_transcript(video_id, language=language)
                    if not transcript:
                        error = "Could not generate transcript."
                    elif GOOGLE_API_KEY:
                        summary = summarize_with_gemini(transcript, GOOGLE_API_KEY, preferred_language=language)
            else:
                error = "Please provide a YouTube URL or upload a video file."
        except Exception as e:
            error = str(e)
        return render_template('youtube_transcript.html', transcript=transcript, summary=summary, error=error)
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

@app.route('/convert_text_to_script', methods=['GET', 'POST'])
def convert_text_to_script():
    if request.method == 'POST':
        text_input = request.form.get('text_input')
        text_file = request.files.get('text_file')
        script_style = request.form.get('script_style')
        output_language = request.form.get('output_language', 'en')
        final_text = text_input or ''

        if text_file and text_file.filename != '':
            try:
                if text_file.content_type.startswith('text/') or text_file.filename.endswith(('.txt', '.md')):
                    final_text = text_file.read().decode('utf-8')
                else:
                    return render_template('convert_text_to_script.html', error="Invalid file type. Please upload a text file (e.g., .txt, .md).", text_input=text_input)
            except Exception as e:
                app.logger.error(f"Error reading uploaded file: {e}")
                return render_template('convert_text_to_script.html', error=f"Error reading uploaded file: {str(e)}", text_input=text_input)

        if not final_text.strip():
            return render_template('convert_text_to_script.html', error="Text input or a text file is required.", text_input=text_input)
        if not script_style:
            return render_template('convert_text_to_script.html', error="No script style selected.", text_input=final_text)
        if not GOOGLE_API_KEY:
            return render_template('convert_text_to_script.html', error="Google API Key is not configured.", text_input=final_text)
        try:
            generated_script = generate_script_with_gemini(final_text, script_style, output_language)
            return render_template('convert_text_to_script.html', 
                                 generated_script=generated_script, 
                                 text_input=final_text,
                                 output_language=output_language)
        except Exception as e:
            app.logger.error(f"Error generating script: {e}")
            return render_template('convert_text_to_script.html', 
                                 error=f"Error generating script: {str(e)}", 
                                 text_input=final_text,
                                 output_language=output_language)
    return render_template('convert_text_to_script.html')

if __name__ == '__main__':
    # Basic logging configuration
    app.run(host='0.0.0.0', port=8080, debug=True)
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