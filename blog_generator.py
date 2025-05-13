import google.generativeai as genai
from typing import Dict, Optional
import os
from datetime import datetime
from google.cloud import storage

class BlogGenerator:
    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        # Load from environment if not provided
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        self.model_name = model_name or os.getenv("GOOGLE_MODEL", "models/gemini-2.0-flash")
        if not self.api_key:
            raise ValueError("Google API key not found. Set GOOGLE_API_KEY in your .env file.")
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.model_name)

    def _get_prompt_template(self, style: str) -> str:
        templates = {
            'informative': """
            Convert the following script into an informative blog post. The blog post should:
            1. Have a clear introduction
            2. Include relevant examples and use cases
            3. Be structured with headings and subheadings
            4. Be approximately 5 minutes read
            5. Include a conclusion
            6. Be written in a professional but engaging tone
            7. IMPORTANT: Only output the blog post content itself. Do NOT include any extra commentary, confirmations, or responses such as 'ok'.
            
            Script:
            {script}
            """,
            'tutorial': """
            Convert the following script into a tutorial-style blog post. The blog post should:
            1. Start with a clear problem statement
            2. Include step-by-step instructions
            3. Provide code examples or practical demonstrations
            4. Include troubleshooting tips
            5. Be approximately 5 minutes read
            6. End with a summary of key takeaways
            7. IMPORTANT: Only output the blog post content itself. Do NOT include any extra commentary, confirmations, or responses such as 'ok'.
            
            Script:
            {script}
            """,
            'case_study': """
            Convert the following script into a case study blog post. The blog post should:
            1. Present a real-world scenario
            2. Include challenges and solutions
            3. Provide measurable results
            4. Include lessons learned
            5. Be approximately 5 minutes read
            6. End with actionable insights
            7. IMPORTANT: Only output the blog post content itself. Do NOT include any extra commentary, confirmations, or responses such as 'ok'.
            
            Script:
            {script}
            """
        }
        return templates.get(style, templates['informative'])

    def generate_blog_post(self, script: str, style: str = 'informative') -> Dict[str, str]:
        try:
            prompt = self._get_prompt_template(style).format(script=script)
            
            response = self.model.generate_content(prompt)
            
            if not response.text:
                raise ValueError("No content generated from the model")

            # Generate a title from the content
            title_prompt = f"Generate a catchy title for this blog post: {response.text[:200]}..."
            title_response = self.model.generate_content(title_prompt)
            
            return {
                'title': title_response.text.strip(),
                'content': response.text,
                'generated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
        except Exception as e:
            raise Exception(f"Error generating blog post: {str(e)}")

    def format_html(self, blog_data: Dict[str, str]) -> str:
        html_template = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{blog_data['title']}</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                h1 {{
                    color: #333;
                    border-bottom: 2px solid #eee;
                    padding-bottom: 10px;
                }}
                h2 {{
                    color: #444;
                    margin-top: 30px;
                }}
                p {{
                    margin-bottom: 20px;
                }}
                .meta {{
                    color: #666;
                    font-style: italic;
                    margin-bottom: 30px;
                }}
            </style>
        </head>
        <body>
            <h1>{blog_data['title']}</h1>
            <div class="meta">Generated on: {blog_data['generated_at']}</div>
            {blog_data['content']}
        </body>
        </html>
        """
        return html_template

GCS_BUCKET_NAME = 'startup-consulting'

def upload_to_gcs(local_file_path, destination_blob_name):
    storage_client = storage.Client()
    bucket = storage_client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(local_file_path)
    return blob.public_url
# Use upload_to_gcs after saving blog HTML files, and return the GCS URL for download or sharing. 