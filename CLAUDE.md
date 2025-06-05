# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Running the Application
```bash
# Local development
python app.py

# With virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate
python app.py

# Using Docker
docker build -t voice-app .
docker run -p 8080:8080 voice-app
```

### Dependencies
```bash
# Install Python dependencies
pip install -r requirements.txt

# Essential system dependencies (required for audio/video processing)
# On Ubuntu/Debian:
apt-get install ffmpeg

# On macOS:
brew install ffmpeg

# For Google Cloud deployment, ensure you have:
# - Google Cloud SDK installed and configured
# - Service account with Storage permissions for file uploads
```

### Testing and Validation
- No automated test suite exists - manual testing through web interface required
- Test each feature independently:
  - Script to podcast conversion: `/convert_podcast`
  - Presentation to script: `/convert_presentation_to_script` 
  - Blog generation: `/convert_to_blog`
  - YouTube transcript: `/youtube_transcript`
  - Audio transcript: `/audio_transcript`

### Deployment
```bash
# Google Cloud Build
gcloud builds submit --config cloudbuild.yaml

# Environment variables required:
# MURFA_API_KEY - Murf AI text-to-speech API key
# GEMINI_API_KEY - Google Gemini AI API key  
# GCS_BUCKET_NAME - Google Cloud Storage bucket (default: "startup-consulting")
```

## Architecture Overview

### Core Application Structure
This is a Flask web application that provides AI-powered content conversion tools. The application follows a modular blueprint architecture:

- **Main Flask App** (`app.py`): Central routing and application configuration
- **Blueprint Modules**: Self-contained feature modules for specific conversions
  - `podcast_generator.py`: Script-to-audio conversion using Murf AI
  - `presentation_converter.py`: PowerPoint/PDF to script conversion using Gemini AI
  - `blog_generator.py`: Text-to-blog conversion
  - `youtube_transcript.py`: YouTube video transcription and summarization
  - `audio_transcript.py`: Audio file transcription

### Key Integration Points

**AI Services Integration:**
- **Murf AI**: Text-to-speech with multi-voice support and language detection
- **Google Gemini**: Content generation, script creation, and summarization
- **Speech Recognition**: Audio transcription with chunking for large files

**File Storage:**
- Local temporary processing in `output_audio/` and `output_blog/`
- Google Cloud Storage for permanent file storage with signed URLs
- Automatic cleanup of local files after upload

**Multi-language Support:**
- Korean and English detection and processing
- Language-specific voice assignments in `murf_voices.py`
- Localized AI prompts and outputs

### Data Flow Architecture

1. **Input Processing**: File uploads (PPTX, PDF, audio, video) or text input
2. **Content Extraction**: Format-specific parsers extract text content
3. **AI Processing**: Gemini generates scripts/blogs or processes transcripts
4. **Audio Generation**: Murf converts scripts to speech with speaker assignment
5. **Output Storage**: Files uploaded to GCS with signed URLs for download

### Voice Configuration System
The application uses a sophisticated voice mapping system:
- Language detection determines Korean vs English voices
- Speaker roles (HOST, Voice1, etc.) mapped to specific voice IDs
- Conversational style applied consistently across generated audio

### Blueprint Registration Pattern
Each feature module follows the Flask blueprint pattern for modular organization:
```python
# In app.py
from presentation_converter import presentation_bp
from podcast_generator import podcast_bp
app.register_blueprint(podcast_bp)
app.register_blueprint(presentation_bp)
```

### Error Handling Strategy
- Comprehensive logging throughout the application
- User-friendly error messages in templates
- Graceful API failure handling with fallbacks
- Temporary file cleanup on errors

## Important Implementation Details

### File Processing Patterns
- All uploaded files are processed in temporary locations and cleaned up after use
- Audio files are processed in chunks for large files to avoid memory issues
- Generated files are immediately uploaded to GCS and local copies removed

### API Integration Patterns
- **Murf AI Error Handling**: Special handling for 502 errors (Bad Gateway) with user-friendly messages
- **Gemini API**: Uses `gemini-2.0-flash` model by default, configurable via `GOOGLE_MODEL` env var
- **Language Detection**: Automatic detection of Korean vs English text using character frequency analysis

### Security Considerations
- API keys loaded via environment variables only
- Temporary files use UUID-based naming to prevent conflicts
- GCS signed URLs provide time-limited access to generated files
- File upload validation by content type and extension

### Performance Optimizations
- Audio segments processed and combined sequentially to manage memory usage
- Chunked transcription for long audio/video files
- Automatic cleanup of temporary files to prevent storage bloat

## Common Issues and Solutions

### Audio Generation Failures
- Check Murf API key validity and account status
- Verify voice IDs match available voices for selected language
- Ensure script follows proper "SPEAKER: text" format

### Transcription Issues
- Verify ffmpeg is installed and accessible
- Check audio file formats are supported (MP3, WAV, M4A, FLAC, OGG)
- For long files, processing happens in chunks automatically

### GCS Upload Failures
- Ensure GCS_BUCKET_NAME environment variable is set
- Verify Google Cloud authentication is configured
- Check bucket permissions for the service account