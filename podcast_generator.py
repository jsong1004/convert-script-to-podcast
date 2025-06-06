import os
import uuid
import requests
import io
from flask import Blueprint, render_template, request, current_app, url_for
from murf import Murf
from pydub import AudioSegment
from google.cloud import storage
import re
from gcs_utils import upload_to_gcs, generate_gcs_signed_url

# Ensure MURFA_API_KEY is loaded
MURFA_API_KEY = os.getenv("MURFA_API_KEY")

DEPLOYMENT_ENV = os.getenv("DEPLOYMENT_ENV", "local")

podcast_bp = Blueprint('podcast_bp', __name__, template_folder='../templates')

def detect_language(text):
    """Detect if the text is primarily Korean or English."""
    # Count Korean characters (Hangul)
    korean_chars = len(re.findall(r'[가-힣]', text))
    # Count English characters
    english_chars = len(re.findall(r'[a-zA-Z]', text))
    
    # If there are more Korean characters than English, consider it Korean
    return 'ko' if korean_chars > english_chars else 'en'

def parse_script(script_text):
    lines = script_text.strip().split('\n')
    parsed_script = []
    for line in lines:
        line = line.strip()
        if ':' in line:
            parts = line.split(':', 1)
            speaker = parts[0].strip()
            text = parts[1].strip()
            if speaker and text:
                parsed_script.append({'speaker': speaker, 'text': text})
        elif line:
            current_app.logger.info(f"Skipping line without speaker: {line}")
    return parsed_script

def get_voice_config(speaker_name, output_language='en'):
    speaker_name_upper = speaker_name.upper()
    if output_language == 'ko':
        if speaker_name_upper == "HOST":
            return "ko-KR-jong-su"  # Male voice for HOST
        else:
            return "ko-KR-jangmi"   # Female voice for others
    else:
        if speaker_name_upper == "HOST":
            return "en-US-ryan"
        elif speaker_name_upper == "VOICE 1":
            return "en-US-natalie"
        elif speaker_name_upper == "VOICE 2":
            return "en-US-natalie"
        else:
            current_app.logger.warning(f"Speaker '{speaker_name}' not recognized, using default voice.")
            return "en-US-natalie"

@podcast_bp.route('/convert_script_to_podcast', methods=['GET', 'POST'])
def convert_script_to_podcast():
    script_text_from_area = ""
    if request.method == 'POST':
        script_text_from_area = request.form.get('script')
        script_file = request.files.get('script_file')
        final_script_text = ""

        if script_file and script_file.filename != '':
            try:
                if script_file.content_type.startswith('text/'):
                    final_script_text = script_file.read().decode('utf-8')
                    current_app.logger.info(f"Successfully read script from uploaded file: {script_file.filename}")
                else:
                    return render_template('convert_podcast.html', error="Invalid file type. Please upload a text file.", script_text=script_text_from_area)
            except Exception as e:
                current_app.logger.error(f"Error reading uploaded file: {e}")
                return render_template('convert_podcast.html', error=f"Error reading uploaded file: {str(e)}", script_text=script_text_from_area)
        elif script_text_from_area:
            final_script_text = script_text_from_area
        else:
            return render_template('convert_podcast.html', error="Script text or a script file is required.", script_text=script_text_from_area)

        if not final_script_text.strip():
             return render_template('convert_podcast.html', error="Script content is empty.", script_text=script_text_from_area)

        if not MURFA_API_KEY:
            return render_template('convert_podcast.html', error="Murf AI API Key is not configured.", script_text=final_script_text)

        try:
            current_app.logger.info("Starting audio generation process for script-to-podcast.")
            parsed_script = parse_script(final_script_text)
            if not parsed_script:
                return render_template('convert_podcast.html', error="Could not parse the script. Ensure 'SPEAKER: Text' format.", script_text=final_script_text)

            # Detect language from the first non-empty text segment
            output_language = 'en'  # default
            for item in parsed_script:
                if item['text'].strip():
                    output_language = detect_language(item['text'])
                    current_app.logger.info(f"Detected language: {output_language}")
                    break

            audio_segments = []
            murf_client = Murf(api_key=MURFA_API_KEY)
            current_app.logger.info(f"Parsed script for podcast: {parsed_script}")

            for i, item in enumerate(parsed_script):
                current_app.logger.info(f"Processing segment {i+1}/{len(parsed_script)}: Speaker: {item['speaker']}")
                voice_id = get_voice_config(item['speaker'], output_language=output_language)
                
                tts_response = murf_client.text_to_speech.generate(text=item['text'], voice_id=voice_id)
                audio_url = tts_response.audio_file
                current_app.logger.info(f"Audio URL from Murf: {audio_url}")

                audio_download_response = requests.get(audio_url)
                audio_download_response.raise_for_status()
                
                file_extension = audio_url.split('?')[0].split('.')[-1].lower()
                if file_extension not in ['mp3', 'wav', 'ogg', 'flv', 'aac']:
                    current_app.logger.warning(f"Unexpected audio file extension '{file_extension}', defaulting to wav.")
                    file_extension = "wav"

                segment_audio = AudioSegment.from_file(io.BytesIO(audio_download_response.content), format=file_extension)
                audio_segments.append(segment_audio)
                current_app.logger.info(f"Segment {i+1} processed.")

            if not audio_segments:
                return render_template('convert_podcast.html', error="No audio segments generated.", script_text=final_script_text)

            combined_audio = AudioSegment.empty()
            for segment in audio_segments:
                combined_audio += segment
            
            unique_filename = f"podcast_audio_{uuid.uuid4().hex}.mp3"
            output_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
            
            current_app.logger.info(f"Exporting combined podcast audio to {output_path}")
            combined_audio.export(output_path, format="mp3")

            print(f"DEPLOYMENT_ENV: {DEPLOYMENT_ENV}")
            current_app.logger.info(f"DEPLOYMENT_ENV: {DEPLOYMENT_ENV}")
            
            if DEPLOYMENT_ENV == "cloud":
                gcs_blob_name = unique_filename  # or f"audio/{unique_filename}" if you use a subfolder
                gcs_url = upload_to_gcs(output_path, gcs_blob_name)
                signed_url = generate_gcs_signed_url(gcs_blob_name)
                print(f"GCS URL: {signed_url}")
                current_app.logger.info(f"GCS URL: {signed_url}")
                if os.path.exists(output_path):
                    os.remove(output_path)
                return render_template('convert_podcast.html', audio_file_url=signed_url, script_text=final_script_text)
            else:
                audio_file_url = url_for('download_file', filename=unique_filename, _external=False)
            return render_template('convert_podcast.html', audio_file_url=audio_file_url, script_text=final_script_text)

        except requests.exceptions.HTTPError as http_err:
            current_app.logger.error(f"HTTP error during Murf API audio download: {http_err}")
            return render_template('convert_podcast.html', error=f"HTTP error with Murf: {http_err}", script_text=final_script_text)
        except Murf.ApiError as murf_api_err:
            current_app.logger.error(f"Murf API Error: {murf_api_err}", exc_info=True)
            error_message = f"Murf API Error (Status {murf_api_err.status_code}). "
            if murf_api_err.status_code == 502:
                 error_message += "Temporary Murf service issue. Try again."
            else:
                error_message += "Check script, API key, and Murf account."
            return render_template('convert_podcast.html', error=error_message, script_text=final_script_text)
        except Exception as e:
            current_app.logger.error(f"Error during podcast generation: {e}", exc_info=True)
            return render_template('convert_podcast.html', error=f"Unexpected error: {str(e)}", script_text=final_script_text)

    return render_template('convert_podcast.html', script_text=script_text_from_area)