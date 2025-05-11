# AI Voice & Script Tools

A Flask-based web application that provides AI-powered tools for converting content between different formats. The application uses Murf AI for voice synthesis and Google Gemini for content generation.

## Features

### 1. Presentation to Script Converter
- Convert PowerPoint presentations (PPTX) and PDFs into engaging scripts
- Multiple script styles available (podcast, speech)
- Maintains presentation flow and structure
- Uses Google Gemini AI for natural script generation

### 2. Script to Podcast Generator
- Transform scripts into professional podcasts
- Multiple voice options using Murf AI
- High-quality audio output
- Support for multiple speakers in the script
- Easy script formatting with speaker labels

### 3. Script to Blog Converter
- Convert scripts into well-structured blog posts
- Multiple blog styles (informative, tutorial, case study)
- SEO-friendly content generation
- HTML export option
- Markdown support

### 4. YouTube Transcript Generator
- Extract transcripts from YouTube videos
- Support for multiple languages
- Automatic language detection and fallback
- AI-powered summary generation using Google Gemini
- Clean and readable transcript formatting
- Support for various YouTube URL formats (standard, shorts, live streams)

### 5. Audio Transcript Generator
- Converts audio files to text transcripts
- Supports multiple audio formats:
  - WAV
  - MP3
  - M4A
  - FLAC
  - OGG
- Features:
  - Multi-language support
  - Automatic audio preprocessing
  - Chunk processing for large files
  - Robust error handling and retry logic
  - Audio normalization and optimization
  - Clean temporary file management

## Prerequisites

- Python 3.8 or higher
- Murf AI API key
- Google Gemini API key

## Installation

1. Clone the repository:
```bash
git clone https://github.com/jsong1004/convert-script-to-podcast
cd voice
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the project root with your API keys:
```
MURFA_API_KEY=your_murf_api_key
GOOGLE_API_KEY=your_google_api_key
```

## Usage

1. Start the Flask application:
```bash
python app.py
```

2. Open your web browser and navigate to `http://localhost:5000`

3. Choose the desired tool:
   - **Presentation to Script**: Upload a PPTX or PDF file and select the script style
   - **Script to Podcast**: Enter or upload a script and generate audio
   - **Script to Blog**: Convert your script into a blog post with your preferred style
   - **YouTube Transcript**: Enter a YouTube URL to extract and summarize the transcript
   - **Audio Transcript**: Upload an audio file to extract the transcript

## Project Structure

```
voice/
├── app.py              # Main Flask application
├── blog_generator.py   # Blog generation module
├── podcast_generator.py # Podcast generation module
├── presentation_converter.py # Presentation conversion module
├── youtube_transcript.py # YouTube transcript module
├── audio_transcript.py  # Audio transcript module
├── requirements.txt    # Project dependencies
├── templates/         # HTML templates
│   ├── base.html
│   ├── index.html
│   ├── convert_presentation.html
│   ├── convert_to_blog.html
│   ├── youtube_transcript.html
│   └── audio_transcript.html
├── static/           # Static files (CSS, JS)
└── output_audio/     # Generated audio files
```

## API Integration

### Murf AI
- Used for text-to-speech conversion
- Supports multiple voices and styles
- Generates high-quality audio output

### Google Gemini
- Powers content generation for scripts and blog posts
- Provides natural language processing capabilities
- Ensures high-quality content output
- Generates summaries for YouTube transcripts

### YouTube Transcript API
- Extracts transcripts from YouTube videos
- Supports multiple languages
- Handles various YouTube URL formats
- Provides fallback options for unavailable languages

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support, please open an issue in the GitHub repository or contact the maintainers.