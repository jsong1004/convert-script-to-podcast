# AI Voice Tools Hub

A Flask web application that provides multiple tools for voice and presentation content creation:
1. Convert written dialogue scripts into professional podcasts using Murf AI
2. Transform PowerPoint presentations into engaging scripts
3. Convert PDF documents into podcast-ready scripts

## Description

The AI Voice Tools Hub is a comprehensive suite of tools for content creators, educators, and storytellers to produce engaging audio content without the need for recording equipment or voice actors. The application offers multiple features:

- **Script to Podcast**: Transform written dialogue scripts with multiple speakers into professional-sounding podcasts
- **Presentation to Script**: Convert PowerPoint presentations into engaging, spoken-word scripts
- **PDF to Script**: Transform PDF documents into podcast-ready scripts
- **AI-Powered Script Generation**: Uses Google's Gemini AI to create natural, engaging scripts from presentation content
- **Multiple Voice Support**: Automatically assigns different voices to different characters
- **Professional Text-to-Speech**: Uses Murf AI's high-quality voice synthesis
- **Easy Download**: Get your podcast as a downloadable audio file
- **User-Friendly Interface**: Simple web interface with minimal learning curve

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

### Setup

1. Clone the repository:
   ```
   git clone https://github.com/jsong1004/voice.git
   cd voice
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Set up your API keys in a `.env` file:
   ```
   MURFA_API_KEY=your_murf_api_key_here
   GOOGLE_API_KEY=your_google_api_key_here
   ```

## Usage

1. Start the Flask application:
   ```
   python app.py
   ```

2. Open your web browser and navigate to:
   ```
   http://localhost:5000
   ```

3. Choose your desired tool:
   - **Script to Podcast**: Enter your script in the provided text area
   - **Presentation to Script**: Upload a PowerPoint (.pptx) or PDF file
   - **PDF to Script**: Upload a PDF document

### Script Format Example

```
HOST: Welcome to Tech Talk, where we discuss the latest in technology trends.
Voice 1: Thanks for having me on the show, I'm excited to share my insights.
HOST: Today we're talking about the future of artificial intelligence. What major developments do you see coming?
Voice 1: I think we'll see more integration of AI into everyday objects, creating truly smart environments.
Voice 2: I agree, but I also think we'll face new ethical challenges as AI becomes more autonomous.
HOST: That's a great point about ethics. How should we approach regulation?
Voice 2: We need a balanced approach that encourages innovation while protecting against potential risks.
```

### Presentation/PDF Conversion

When converting presentations or PDFs, you can choose between two script styles:
- **Podcast Style**: Creates a multi-voice conversation format
- **Speech Style**: Generates a single-speaker presentation format

## Voice Configuration

- HOST voice: en-US-ryan (Conversational style)
- Other voices: Various options from Murf AI's voice library

## API Reference

This application uses multiple APIs:
- [Murf AI](https://murf.ai/) for text-to-speech conversion
- [Google Gemini](https://ai.google.dev/) for AI-powered script generation

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [Murf AI](https://murf.ai/) for their text-to-speech API
- [Google Gemini](https://ai.google.dev/) for AI-powered script generation
- [Flask](https://flask.palletsprojects.com/) web framework