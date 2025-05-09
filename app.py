import os
from flask import Flask, render_template, request, send_from_directory, jsonify
from dotenv import load_dotenv
from murf import Murf # Uncommented
from pydub import AudioSegment # Uncommented
import uuid # For generating unique filenames
import requests # For downloading audio from Murf AI if it provides a URL
import io # For handling audio bytes
import logging # Add this line to import the logging module

load_dotenv()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'output_audio' # Folder to save generated audio files

# Ensure the output folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

MURFA_API_KEY = os.getenv("MURFA_API_KEY")
if not MURFA_API_KEY:
    print("Error: MURFA_API_KEY not found in .env file. Please set it and restart the application.")
    # In a production app, you might want to prevent the app from starting or show an error page.

# --- Helper functions ---
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

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        script_text_from_area = request.form.get('script')
        script_file = request.files.get('script_file')
        final_script_text = ""

        if script_file and script_file.filename != '':
            try:
                # Ensure it's a text-based file, very basic check
                if script_file.content_type.startswith('text/'):
                    final_script_text = script_file.read().decode('utf-8')
                    app.logger.info(f"Successfully read script from uploaded file: {script_file.filename}")
                else:
                    return render_template('index.html', error="Invalid file type. Please upload a text file (e.g., .txt, .md).", script_text=script_text_from_area)
            except Exception as e:
                app.logger.error(f"Error reading uploaded file: {e}")
                return render_template('index.html', error=f"Error reading uploaded file: {str(e)}", script_text=script_text_from_area)
        elif script_text_from_area:
            final_script_text = script_text_from_area
        else:
            return render_template('index.html', error="Script text or a script file is required.")

        if not final_script_text.strip():
             return render_template('index.html', error="Script content is empty.", script_text=script_text_from_area)

        if not MURFA_API_KEY:
            return render_template('index.html', error="Murf AI API Key is not configured. Please contact the administrator.", script_text=final_script_text)

        try:
            app.logger.info("Starting audio generation process.")
            parsed_script = parse_script(final_script_text)
            if not parsed_script:
                return render_template('index.html', error="Could not parse the script. Ensure it follows 'SPEAKER: Text' format or the file content is valid.", script_text=final_script_text)

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
                # The log indicates the URL points to a .wav file.
                file_extension = audio_url.split('?')[0].split('.')[-1].lower()
                if file_extension not in ['mp3', 'wav', 'ogg', 'flv', 'aac']: # Add other formats if Murf returns them
                    app.logger.warning(f"Unexpected audio file extension '{file_extension}' from Murf, attempting to load as wav.")
                    file_extension = "wav" # Default to wav if unsure, or handle error

                segment_audio = AudioSegment.from_file(io.BytesIO(audio_download_response.content), format=file_extension)
                audio_segments.append(segment_audio)
                app.logger.info(f"Segment {i+1} processed and added from URL.")

            if not audio_segments:
                return render_template('index.html', error="No audio segments were generated. Check script and API logs.", script_text=script_text)

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

            app.logger.info("Audio generation successful.")
            return render_template('index.html', audio_file_url=f"/download/{unique_filename}", script_text=final_script_text)

        except requests.exceptions.HTTPError as http_err:
            app.logger.error(f"HTTP error during Murf API audio download: {http_err}")
            app.logger.error(f"Response content: {http_err.response.content if http_err.response else 'No response content'}")
            return render_template('index.html', error=f"An HTTP error occurred while downloading audio from Murf: {http_err}", script_text=final_script_text)
        except Murf.ApiError as murf_api_err: # Specifically catch Murf API errors
            app.logger.error(f"Murf API Error: Status {murf_api_err.status_code}, Body: {murf_api_err.body}", exc_info=True)
            error_message = f"Murf API Error (Status {murf_api_err.status_code}). "
            if murf_api_err.status_code == 502:
                error_message += "This might be a temporary issue with the Murf AI service (Bad Gateway). Please try again shortly or check the voice ID and text segment."
            else:
                error_message += "Please check your script, API key, and Murf AI account status."
            return render_template('index.html', error=error_message, script_text=final_script_text)
        except Exception as e:
            app.logger.error(f"Error during audio generation: {e}", exc_info=True)
            return render_template('index.html', error=f"An unexpected error occurred: {str(e)}", script_text=final_script_text)

    return render_template('index.html')

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

if __name__ == '__main__':
    # Basic logging configuration
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    app.run(debug=True)