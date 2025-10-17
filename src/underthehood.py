import requests
import asyncio
import os
from src.github import create_repo, push, github_page


github_username = os.getenv("github_username")


def _generate_code_via_api(brief: str, checks: list, attachments: list, existing_code: str = "") -> dict:
    """
    Generate code using direct API calls (no Pydantic AI)
    Returns dictionary mapping filenames to file contents
    
    Args:
        brief: Task description
        checks: Evaluation criteria
        attachments: Sample files
        existing_code: Existing code for modifications (empty for round 1)
    
    Returns:
        dict: Generated files {filename: content}
    """
    
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL", "https://aipipe.org/openai/v1")
    model = "gpt-4o-mini"
    
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")
    
    # Build the system prompt
    system_prompt = """You are an expert professional web developer.
Generate production-ready, well-structured code that follows best practices.
Always include comprehensive documentation and error handling.
IMPORTANT: Return ONLY a valid JSON object mapping filenames to file contents.
Example format:
{
  "index.html": "<!DOCTYPE html>...",
  "style.css": "body { ... }",
  "script.js": "function main() { ... }",
  "README.md": "# Project Title...",
  "LICENSE": "MIT License..."
}
Ensure all strings are properly escaped for valid JSON.
Do not include markdown code fences or any text outside the JSON."""
    
    # Build the user prompt
    if existing_code:
        # Modification round
        user_prompt = f"""Modify the existing web application code.
EXISTING CODE:
{existing_code}
NEW REQUIREMENTS/MODIFICATIONS:
{brief}
EVALUATION CRITERIA:
{chr(10).join(f"- {check}" for check in checks)}
TASK:
1. Modify the existing code to meet the new requirements
2. Ensure all evaluation criteria are met
3. Return ALL files (modified and unmodified)
4. Maintain code quality and best practices
5. Code must be production-ready
Important: Return ONLY the JSON object with all files."""
    else:
        # Initial generation round
        user_prompt = f"""Generate a complete web application.
TASK DESCRIPTION:
{brief}
EVALUATION CRITERIA:
{chr(10).join(f"- {check}" for check in checks)}
SAMPLE DATA/REFERENCE:
{attachments if attachments else "No sample files provided"}
REQUIREMENTS:
1. Generate a complete, production-ready web application
2. Include all necessary files (HTML, CSS, JavaScript, etc.)
3. The code must pass all evaluation criteria
4. Follow best practices and industry standards
5. Include proper error handling and validation
6. Write clean, well-documented code
REQUIRED FILES:
- index.html (main application file with all HTML)
- style.css (complete styling with modern design)
- script.js (JavaScript if functionality needed)
- README.md (comprehensive documentation including installation, features, usage)
- LICENSE (MIT License text)
Important: Return ONLY the JSON object with all files. Make sure each file is complete and functional."""
    
    # Make API request
    try:
        url = base_url.rstrip("/") + "/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.3,
        }
        
        print(f"Generating code from: {base_url}")
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        
        if response.status_code != 200:
            print(f"API Error: {response.status_code}")
            print(f"Response: {response.text}")
            raise Exception(f"API returned status {response.status_code}")
        
        # Extract content from response
        content = response.json()["choices"][0]["message"]["content"].strip()
        print(f"Generated content length: {len(content)}")
        
        # Parse JSON
        import json
        import re
        
        try:
            # Try direct JSON parsing first
            files = json.loads(content)
        except json.JSONDecodeError:
            # Try to extract JSON from code fences if present
            match = re.search(r"```(?:json)?\s*\n?([\s\S]*?)\n?```", content)
            if match:
                files = json.loads(match.group(1))
            else:
                # Try to find JSON object manually
                json_start = content.find('{')
                json_end = content.rfind('}') + 1
                if json_start != -1 and json_end > json_start:
                    files = json.loads(content[json_start:json_end])
                else:
                    raise ValueError("Could not parse JSON from response")
        
        # Validate and clean files
        if not isinstance(files, dict):
            raise ValueError("Response is not a JSON object")
        
        # Ensure all files are strings
        cleaned_files = {}
        for filename, content in files.items():
            if isinstance(content, str):
                cleaned_files[filename] = content
            else:
                cleaned_files[filename] = str(content)
        
        # Ensure required files exist
        if "LICENSE" not in cleaned_files:
            cleaned_files["LICENSE"] = """MIT License
Copyright (c) 2025
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE."""
        
        if "README.md" not in cleaned_files:
            cleaned_files["README.md"] = f"""# Generated Web Application
## Overview
{brief[:100]}...
## Installation
1. Clone the repository
2. Open `index.html` in your web browser
3. No additional setup required
## Features
- Production-ready code
- Clean and maintainable structure
- Fully functional implementation
- Professional documentation
## License
This project is licensed under the MIT License - see the LICENSE file for details.
"""
        
        print(f"✓ Generated {len(cleaned_files)} files")
        return cleaned_files
        
    except Exception as e:
        print(f"Code generation failed: {e}")
        raise


async def process_task(request: dict):
    """
    Main task processing workflow:
    1. Extract request data
    2. Generate code
    3. Create/update GitHub repository
    4. Push code to GitHub
    5. Enable GitHub Pages
    6. Notify evaluation endpoint
    
    Args:
        request: Dictionary containing task details from API
    """
    try:
        # Extract request data
        email = request['email']
        task_id = request['task']
        round_count = request['round']
        nonce = request['nonce']
        brief = request['brief']
        checks = request['checks']
        attachments = request['attachments']
        evaluation_url = request['evaluation_url']
        
        print(f"\n{'='*60}")
        print(f"PROCESSING TASK")
        print(f"Task ID: {task_id} | Round: {round_count}")
        print(f"{'='*60}\n")
        
        # Step 1: Get existing code if this is a modification round
        existing_code = ""
        if round_count > 1:
            try:
                from src.github import get_repo
                repo_name = f"project-1-{nonce}"
                existing_files = get_repo(repo_name)
                
                # Format existing code for the prompt
                existing_code = "\n".join(
                    f"=== {filename} ===\n{content}\n"
                    for filename, content in existing_files.items()
                )
                print(f"✓ Fetched existing code from {repo_name}")
            except Exception as e:
                print(f"⚠ Warning: Could not fetch existing files: {e}")
                existing_code = ""
        
        # Step 2: Generate code
        print("Generating code...")
        files = _generate_code_via_api(brief, checks, attachments, existing_code)
        print(f"✓ Generated {len(files)} files")
        
        # Step 3: Handle repository (create on round 1, use existing on round > 1)
        if round_count == 1:
            print("Creating new GitHub repository...")
            repo = create_repo(nonce)
            repo_name = repo['repo_name']
            repo_url = repo['repo_url']
            print(f"✓ Repository created: {repo_name}")
        else:
            repo_name = f"project-1-{nonce}"
            repo_url = f"https://github.com/{github_username}/{repo_name}"
            print(f"Updating existing repository: {repo_name}")
        
        # Step 4: Push files to GitHub
        print("Pushing files to GitHub...")
        sha = push(repo_name, files, round_count )
        print(f"✓ Pushed with commit SHA: {sha}")
        
        # Step 5: Enable GitHub Pages (only on first round)
        if round_count == 1:
            print("Enabling GitHub Pages...")
            try:
                github_page(repo_name)
                print(f"✓ GitHub Pages enabled")
            except Exception as e:
                print(f"⚠ Warning: Could not enable GitHub Pages: {e}")
        
        # Wait for pages to become available
        await asyncio.sleep(2)
        page_url = f"https://{github_username}.github.io/{repo_name}/"
        print(f"GitHub Pages URL: {page_url}")
        
        # Step 6: Notify evaluation endpoint
        print("Notifying evaluation endpoint...")
        payload = {
            "email": email,
            "task": task_id,
            "round": round_count,
            "nonce": nonce,
            "repo_url": repo_url,
            "commit_sha": sha,
            "pages_url": page_url,
        }
        
        # Retry logic for notification
        notification_sent = False
        for attempt in range(5):
            try:
                response = requests.post(
                    evaluation_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=30,
                )
                if response.status_code == 200:
                    notification_sent = True
                    print(f"✓ Evaluation endpoint notified successfully")
                    break
                else:
                    print(f"⚠ Attempt {attempt + 1}: Got status {response.status_code}")
            except Exception as e:
                print(f"⚠ Attempt {attempt + 1}: Error notifying evaluation_url: {e}")
            
            if attempt < 4:
                await asyncio.sleep(2 ** attempt)
        
        if not notification_sent:
            print("⚠ Warning: Could not notify evaluation endpoint after 5 attempts")
        
        print(f"\n{'='*60}")
        print(f"✓ TASK PROCESSING COMPLETED")
        print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"\n{'='*60}")
        print(f"✗ BACKGROUND PROCESSING ERROR: {e}")
        print(f"{'='*60}\n")
        import traceback
        traceback.print_exc()
