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

## Project Structure

```
voice/
├── app.py              # Main Flask application
├── blog_generator.py   # Blog generation module
├── podcast_generator.py # Podcast generation module
├── presentation_converter.py # Presentation conversion module
├── requirements.txt    # Project dependencies
├── templates/         # HTML templates
│   ├── base.html
│   ├── index.html
│   ├── convert_presentation.html
│   ├── convert_to_blog.html
│   └── ...
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