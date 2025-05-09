# Convert Audio Script to a Podcast

A Flask web application that transforms written dialogue scripts with multiple speakers into professional-sounding podcasts using Murf AI's text-to-speech technology.

## Description

The "Convert Audio Script to a Podcast" application allows content creators, educators, and storytellers to produce engaging audio content without the need for recording equipment or voice actors. Users can input scripts with a host and multiple character voices, each rendered with distinct, natural-sounding voices.

## Features

- **Simple Script Format**: Enter dialogue using an intuitive format (HOST:, Voice 1:, Voice 2:, etc.)
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
   git clone https://github.com/jsong1004/convert-script-to-podcast.git
   cd convert-script-to-podcast
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

4. Set up your Murf AI API key:
   ```
   # On Windows
   set MURF_API_KEY=your_api_key_here
   
   # On macOS/Linux
   export MURF_API_KEY=your_api_key_here
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

3. Enter your script in the provided text area using the following format:
   ```
   HOST: Welcome to our podcast on artificial intelligence!
   Voice 1: Thanks for having me. I'm excited to discuss this topic.
   HOST: Let's start with the basics. What is AI?
   Voice 2: AI refers to systems or machines that mimic human intelligence.
   ```

4. Click "Generate Podcast" and wait for processing

5. Download your podcast when it's ready

## Example Script

```
HOST: Welcome to Tech Talk, where we discuss the latest in technology trends.
Voice 1: Thanks for having me on the show, I'm excited to share my insights.
HOST: Today we're talking about the future of artificial intelligence. What major developments do you see coming?
Voice 1: I think we'll see more integration of AI into everyday objects, creating truly smart environments.
Voice 2: I agree, but I also think we'll face new ethical challenges as AI becomes more autonomous.
HOST: That's a great point about ethics. How should we approach regulation?
Voice 2: We need a balanced approach that encourages innovation while protecting against potential risks.
```

## Voice Configuration

- HOST voice: en-US-freddie (Conversational style)
- Other voices: Various options from Murf AI's voice library

## API Reference

This application uses the Murf AI API for text-to-speech conversion. You will need to obtain an API key from [Murf AI](https://murf.ai/).

Basic API usage:
```python
from murf import Murf

client = Murf(api_key="YOUR_API_KEY")
response = client.text_to_speech.generate(
    text = "Sample text",
    voice_id = "en-US-natalie"
)
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [Murf AI](https://murf.ai/) for their text-to-speech API
- [Flask](https://flask.palletsprojects.com/) web framework