import os
import re
import google.generativeai as genai
from google.generativeai import GenerativeModel

def generate_video_storyboard(user_input, num_clips=4):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise Exception("GEMINI_API_KEY environment variable is required")
    genai.configure(api_key=api_key)
    model = GenerativeModel("gemini-1.5-flash")

    system_prompt = f"""You are tasked with creating a video prompt and voiceover script based on user input. The user will provide specific topics or ideas for video generation.

Input Examples:

"Create a short promo for an eco-friendly coffee brand."
"Create a short promo for business automation using AI."



Output Requirements:

- Generate an 8-second video prompt for a video generation AI model and a voiceover script for TTS (text-to-speech).

- Ensure that the total video/audio duration does not exceed 8 seconds per script.

- If the user specifies a length for the video (e.g., 30 seconds), divide it by 8 to determine the number of scripts. For example, for a 30-second video, generate 4 scripts (30/8 = 3.75, rounded to 4).
If no length is specified, default to 30 seconds.

- Adhere to the language used in the user input. If the input is in Korean, output should be in Korean. If the input is in English, output should be in English.



Output format:

Video Instruction: Cinematic shot of a sunbeam filtering through the leaves of a lush, green coffee plant at sunrise.
Voice Instruction: Keep it friendly and engaging. Keep it friendly and engaging. Keep it friendly and engaging.
Voice: Wake up to a brighter morning. A morning filled with hope, and a better world.

Do NOT include any introductory text, explanations, or extra lines. Do not say things like 'Here are four sets...' or anything else. Only output the {num_clips} sets, each with a Video Prompt and a Voice Script, separated by a blank line."""

    prompt = f"{system_prompt}\n\n{user_input}"

    response = model.generate_content(prompt)
    content = response.text

    regex = r"Video Prompt:\s*(.+?)\s*Voice Script:\s*(.+?)(?=Video Prompt:|$)"
    matches = re.findall(regex, content, re.DOTALL)
    clips = []
    for idx, (video_prompt, voice_script) in enumerate(matches, 1):
        audio_prompt = generate_audio_prompt(video_prompt)
        clips.append({
            "id": f"clip-{idx}",
            "video_prompt": video_prompt.strip(),
            "voice_script": voice_script.strip(),
            "audio_prompt": audio_prompt,
        })
    return clips

def generate_audio_prompt(video_prompt):
    lower_video = video_prompt.lower()
    if any(word in lower_video for word in ['action', 'fast', 'running', 'chase']):
        return 'Energetic, fast-paced orchestral music with driving percussion'
    elif any(word in lower_video for word in ['peaceful', 'calm', 'nature', 'sunset']):
        return 'Peaceful, ambient background music with gentle melodies'
    elif any(word in lower_video for word in ['dramatic', 'intense', 'tension']):
        return 'Dramatic, cinematic music with building tension and orchestral elements'
    elif any(word in lower_video for word in ['happy', 'joyful', 'celebration']):
        return 'Upbeat, cheerful music with light instruments and positive energy'
    else:
        return 'Gentle cinematic background music that complements the visual narrative' 