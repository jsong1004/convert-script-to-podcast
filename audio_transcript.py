import speech_recognition as sr
import os
from pydub import AudioSegment
import tempfile
import time
from requests.exceptions import RequestException
from google.cloud import storage

GCS_BUCKET_NAME = 'startup-consulting'

def preprocess_audio(audio_file_path):
    """Preprocess audio file to ensure compatibility with speech recognition."""
    try:
        # Load the audio file
        audio = AudioSegment.from_file(audio_file_path)
        
        # Convert to mono if stereo
        if audio.channels > 1:
            audio = audio.set_channels(1)
        
        # Set sample rate to 16kHz (optimal for speech recognition)
        audio = audio.set_frame_rate(16000)
        
        # Normalize audio
        audio = audio.normalize()
        
        # Create a temporary file for the processed audio
        temp_processed = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp_processed.close()
        
        # Export the processed audio
        audio.export(temp_processed.name, format='wav')
        return temp_processed.name
    except Exception as e:
        if os.path.exists(temp_processed.name):
            os.unlink(temp_processed.name)
        raise Exception(f"Error preprocessing audio: {str(e)}")

def chunk_audio(audio_file_path, chunk_length_ms=30000):
    """Split audio into smaller chunks for processing."""
    try:
        audio = AudioSegment.from_file(audio_file_path)
        chunks = []
        
        # Split audio into chunks
        for i in range(0, len(audio), chunk_length_ms):
            chunk = audio[i:i + chunk_length_ms]
            # Create temporary file for chunk
            temp_chunk = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            temp_chunk.close()
            # Export chunk
            chunk.export(temp_chunk.name, format='wav')
            chunks.append(temp_chunk.name)
        
        return chunks
    except Exception as e:
        # Clean up any created temporary files
        for chunk_file in chunks:
            if os.path.exists(chunk_file):
                os.unlink(chunk_file)
        raise Exception(f"Error chunking audio: {str(e)}")

def extract_transcript(audio_file_path, language='en-US', max_retries=3, retry_delay=2):
    """Extract transcript from audio file using Google Speech Recognition with retry logic."""
    temp_files = []
    try:
        # Preprocess the audio file
        processed_audio = preprocess_audio(audio_file_path)
        temp_files.append(processed_audio)

        # Split into chunks
        audio = AudioSegment.from_file(processed_audio)
        chunk_length_ms = 30000
        num_chunks = (len(audio) + chunk_length_ms - 1) // chunk_length_ms
        audio_chunks = []
        for i in range(num_chunks):
            start_ms = i * chunk_length_ms
            end_ms = min((i + 1) * chunk_length_ms, len(audio))
            chunk = audio[start_ms:end_ms]
            temp_chunk = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            temp_chunk.close()
            chunk.export(temp_chunk.name, format='wav')
            audio_chunks.append(temp_chunk.name)
        temp_files.extend(audio_chunks)

        recognizer = sr.Recognizer()
        full_transcript = []
        for chunk_file in audio_chunks:
            for attempt in range(max_retries):
                try:
                    with sr.AudioFile(chunk_file) as source:
                        audio_data = recognizer.record(source)
                    chunk_transcript = recognizer.recognize_google(audio_data, language=language)
                    full_transcript.append(chunk_transcript)
                    break
                except sr.UnknownValueError:
                    # If we can't understand this chunk, just skip it
                    break
                except (sr.RequestError, RequestException) as e:
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay * (attempt + 1))
                        continue
                    raise Exception(f"Could not request results from Speech Recognition service after {max_retries} attempts: {str(e)}")

        # Clean up temporary files
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                os.unlink(temp_file)

        if not full_transcript:
            raise Exception("Could not generate transcript from any part of the audio")

        return " ".join(full_transcript)

    except Exception as e:
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
        raise Exception(f"Error processing audio file: {str(e)}")

def get_supported_languages():
    """Return a dictionary of supported languages for speech recognition."""
    return {
        'en-US': 'English (US)',
        'en-GB': 'English (UK)',
        'es-ES': 'Spanish',
        'fr-FR': 'French',
        'de-DE': 'German',
        'it-IT': 'Italian',
        'pt-BR': 'Portuguese (Brazil)',
        'ru-RU': 'Russian',
        'ja-JP': 'Japanese',
        'ko-KR': 'Korean',
        'zh-CN': 'Chinese (Simplified)'
    }

def upload_to_gcs(local_file_path, destination_blob_name):
    storage_client = storage.Client()
    bucket = storage_client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(local_file_path)
    return blob.public_url
# If you want to allow download of processed audio, use upload_to_gcs after exporting or saving any audio file. 