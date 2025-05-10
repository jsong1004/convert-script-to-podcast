# AI Voice Tools Hub - Project Requirements Document

## Project Overview
This project involves developing a Flask web application that provides multiple tools for voice and presentation content creation:
1. Convert written dialogue scripts into professional podcasts using Murf AI
2. Transform PowerPoint presentations into engaging scripts using Google's Gemini AI
3. Convert PDF documents into podcast-ready scripts

## Requirements

### 1. Script to Podcast Conversion
#### User Input
- Users can provide an audio script in the following format:
  ```
  HOST: [Text to be spoken by the host]
  Voice 1: [Text to be spoken by Voice 1]
  Voice 2: [Text to be spoken by Voice 2]
  ...
  ```
- The application supports an arbitrary number of different voices
- Users can input script via text area or file upload (.txt)

#### Voice Configuration
- For the HOST:
  - `voice_id = "en-US-ryan"`
  - `style = "Conversational"`
- For other voices:
  - `voice_id = "en-US-natalie"`
  - `style = "Conversational"`

### 2. Presentation/PDF to Script Conversion
#### File Input
- Support for PowerPoint (.pptx) files
- Support for PDF documents
- File size limit: 16MB
- Input validation for file types

#### Script Generation
- Integration with Google's Gemini AI for script generation
- Two script style options:
  1. Podcast Style (multi-voice conversation)
  2. Speech Style (single-speaker presentation)
- AI-powered content enhancement and natural language processing

### 3. API Integration
#### Murf AI API
- Text-to-speech conversion
- Secure API key handling
- Example usage:
  ```python
  from murf import Murf
  
  client = Murf(api_key="YOUR_API_KEY")
  response = client.text_to_speech.generate(
      text = "Sample text",
      voice_id = "en-US-natalie"
  )
  ```

#### Google Gemini API
- AI-powered script generation
- Secure API key handling
- Content safety checks
- Fallback model support

### 4. Audio Processing
- Parse input script and process each section based on the specified voice
- Combine audio sections into a single file in the correct order
- Support for MP3 output format
- Efficient handling of large audio files

### 5. Flask Web Application
#### User Interface
- Clean, intuitive web interface
- Navigation between different tools
- File upload interface for presentations and PDFs
- Script input area
- Style selection options
- Download link for generated audio
- Error feedback and status messages

#### Routes and Endpoints
- `/`: Main landing page
- `/convert_presentation_to_script`: Presentation/PDF conversion
- `/convert_script_to_podcast`: Script to podcast conversion
- `/download/<filename>`: Audio file download

### 6. Technical Requirements
- Language: Python 3.8+
- Framework: Flask
- Dependencies:
  - Flask>=2.0.0
  - python-dotenv>=0.19.0
  - murf>=0.1.0
  - pydub>=0.25.1
  - requests>=2.26.0
  - google-generativeai>=0.3.0
  - python-pptx>=0.6.21
  - PyPDF2>=3.0.0
- Secure handling of API keys via environment variables

### 7. Error Handling
- Input validation for scripts and files
- API error handling and retry logic
- User-friendly error messages
- Logging for debugging and monitoring
- Graceful handling of large files and timeouts

### 8. Output and Storage
- Generated audio files stored in `output_audio` directory
- Unique filenames using UUID
- Automatic cleanup of temporary files
- Secure file download handling

## Future Enhancements
- Support for more presentation formats
- Additional voice customization options
- Batch processing capabilities
- User authentication and saved preferences
- Real-time preview functionality
- Support for more languages
- Integration with cloud storage services

## Implementation Timeline
1. Core Flask application setup
2. Script to podcast conversion
3. Presentation/PDF conversion
4. AI integration
5. Audio processing
6. User interface development
7. Testing and optimization
8. Deployment

## Development Constraints
- API rate limits and costs
- File size limitations
- Processing time considerations
- Security requirements
- Browser compatibility
- Mobile responsiveness