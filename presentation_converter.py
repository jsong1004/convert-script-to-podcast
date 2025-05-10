import os
import io
from flask import Blueprint, render_template, request, current_app
import google.generativeai as genai
from pptx import Presentation
import PyPDF2

# Ensure GOOGLE_API_KEY is loaded. genai should be configured in app.py
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

presentation_bp = Blueprint('presentation_bp', __name__, template_folder='../templates')

def extract_text_from_pptx(pptx_file_stream):
    """Extracts all text from a .pptx file stream."""
    try:
        prs = Presentation(pptx_file_stream)
        text_runs = []
        for slide in prs.slides:
            for shape in slide.shapes:
                if not shape.has_text_frame:
                    continue
                for paragraph in shape.text_frame.paragraphs:
                    for run in paragraph.runs:
                        text_runs.append(run.text)
        return "\n".join(text_runs)
    except Exception as e:
        current_app.logger.error(f"Error extracting text from PPTX: {e}")
        raise ValueError(f"Could not extract text from presentation: {e}")

def extract_text_from_pdf(pdf_file_stream):
    """Extracts all text from a PDF file stream."""
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file_stream)
        text = []
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            text.append(page.extract_text())
        return "\n".join(text)
    except Exception as e:
        current_app.logger.error(f"Error extracting text from PDF: {e}")
        raise ValueError(f"Could not extract text from PDF: {e}")

def generate_script_with_gemini(presentation_text, script_style):
    """Generates script using Google Gemini API."""
    if not GOOGLE_API_KEY:
        # This check might be redundant if genai.configure in app.py handles it
        current_app.logger.error("Google API Key is not configured for Gemini.")
        raise ValueError("Google API Key is not configured.")

    # Use GOOGLE_MODEL from .env or fallback
    env_model_name = os.getenv("GOOGLE_MODEL")
    primary_model_name = env_model_name if env_model_name else "gemini-1.5-pro"
    fallback_model_name = "gemini-2.0-flash"

    model_name = primary_model_name
    try:
        model = genai.GenerativeModel(model_name)
        current_app.logger.info(f"Successfully initialized Gemini model: {model_name}")
    except Exception as e:
        current_app.logger.error(f"Error initializing Gemini model '{model_name}': {e}")
        if model_name != fallback_model_name: # Avoid re-logging if primary was already the fallback
            current_app.logger.info(f"Attempting to use fallback model: {fallback_model_name}")
            try:
                model_name = fallback_model_name
                model = genai.GenerativeModel(model_name)
                current_app.logger.info(f"Successfully initialized fallback Gemini model: {model_name}")
            except Exception as fallback_e:
                current_app.logger.error(f"Error initializing fallback Gemini model '{model_name}': {fallback_e}")
                raise ValueError(f"Could not initialize Gemini model. Error: {fallback_e}")
        else:
            raise ValueError(f"Could not initialize Gemini model '{model_name}'. Error: {e}")

    common_prompt_instructions = (
        "You are an expert scriptwriter. Convert the following presentation slide content into a spoken script. "
        "The script should be very detailed for each slide concept. "
        "The tone should be passionate, knowledgeable, and educational, like someone speaking engagingly in front of many people. "
        "Include easy-to-understand examples where appropriate to clarify concepts. "
        "Do not include any titles, subtitles, or descriptive slide markers like 'Slide 1 of 5' or 'Next slide'. "
        "Only output the text that will be spoken. Ensure smooth transitions between ideas if they were on different slides."
    )

    if script_style == "podcast":
        style_specific_instructions = (
            "The script should be in a podcast format with multiple voices. "
            "Use 'HOST:' for the main narrator and overall flow. "
            "Use 'VOICE 1:', 'VOICE 2:', etc., for different perspectives, examples, or to break up longer segments of HOST narration. "
            "Ensure a conversational and engaging flow between speakers. The HOST should guide the conversation."
        )
    elif script_style == "speech":
        style_specific_instructions = (
            "The script should be for a single speaker. All text should be attributed to 'HOST:'. "
            "Ensure a continuous, engaging monologue suitable for a keynote presentation."
        )
    else:
        raise ValueError("Invalid script style selected.")

    full_prompt = f"{common_prompt_instructions}\n\n{style_specific_instructions}\n\nPRESENTATION CONTENT:\n---\n{presentation_text}\n---\n\nGENERATED SCRIPT:"

    try:
        current_app.logger.info(f"Sending request to Gemini with model {model_name}. Prompt length: {len(full_prompt)}")
        response = model.generate_content(full_prompt)
        
        if hasattr(response, 'prompt_feedback') and response.prompt_feedback.block_reason:
            current_app.logger.error(f"Gemini content generation blocked. Reason: {response.prompt_feedback.block_reason}")
            current_app.logger.error(f"Block details: {response.prompt_feedback.safety_ratings}")
            raise ValueError(f"Content generation blocked by safety filters. Reason: {response.prompt_feedback.block_reason}")

        if not response.parts:
             current_app.logger.warning(f"Gemini response has no parts. Full response: {response}")
             if hasattr(response, 'text') and response.text:
                 return response.text.strip()
             raise ValueError("Received an empty response from Gemini.")
        
        generated_text = "".join(part.text for part in response.parts if hasattr(part, 'text'))
        if not generated_text.strip():
            current_app.logger.warning(f"Gemini generated empty text. Full response: {response}")
            raise ValueError("Gemini generated an empty script.")
            
        current_app.logger.info("Successfully received script from Gemini.")
        return generated_text.strip()

    except Exception as e:
        current_app.logger.error(f"Error calling Google Gemini API: {e}", exc_info=True)
        if "API key not valid" in str(e) or "PERMISSION_DENIED" in str(e):
             raise ValueError("Google Gemini API Key is invalid or lacks permissions.")
        raise ValueError(f"Failed to generate script using Gemini: {e}")


@presentation_bp.route('/convert_presentation_to_script', methods=['GET', 'POST'])
def convert_presentation_to_script():
    if request.method == 'POST':
        presentation_file = request.files.get('presentation_file')
        script_style = request.form.get('script_style')
        
        if not presentation_file or presentation_file.filename == '':
            return render_template('convert_presentation.html', error="No presentation file selected.")
        
        if not script_style:
            return render_template('convert_presentation.html', error="No script style selected.")

        allowed_extensions = {'pptx', 'pdf'}
        file_ext = presentation_file.filename.rsplit('.', 1)[1].lower() if '.' in presentation_file.filename else ''
        
        if file_ext not in allowed_extensions:
            return render_template('convert_presentation.html', error="Invalid file type. Please upload a .pptx or .pdf file.")

        try:
            current_app.logger.info(f"Processing presentation file: {presentation_file.filename}, style: {script_style}")
            file_stream = io.BytesIO(presentation_file.read())
            
            if file_ext == 'pptx':
                presentation_text = extract_text_from_pptx(file_stream)
            elif file_ext == 'pdf':
                presentation_text = extract_text_from_pdf(file_stream)
            
            if not presentation_text.strip():
                return render_template('convert_presentation.html', error="Could not extract any text from the presentation, or the presentation is empty.")

            current_app.logger.info(f"Extracted text length: {len(presentation_text)}")
            generated_script = generate_script_with_gemini(presentation_text, script_style)
            
            return render_template('convert_presentation.html', generated_script=generated_script)

        except ValueError as ve:
            current_app.logger.error(f"ValueError during presentation conversion: {ve}")
            return render_template('convert_presentation.html', error=str(ve))
        except Exception as e:
            current_app.logger.error(f"Unexpected error during presentation conversion: {e}", exc_info=True)
            return render_template('convert_presentation.html', error=f"An unexpected error occurred: {str(e)}")

    return render_template('convert_presentation.html')