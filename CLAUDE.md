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
# Install dependencies
pip install -r requirements.txt

# Key system dependency (required for audio processing)
# On Ubuntu/Debian: apt-get install ffmpeg
# On macOS: brew install ffmpeg
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