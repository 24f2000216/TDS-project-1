import requests, os, base64

github_token=os.environ.get("github_token")
github_username=os.environ.get("github_username")

def create_repo(id : str):
    #simply create a github repo
    repo_name=f"project-1-{id}"

    url="https://api.github.com/user/repos"
    header={
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    payload={
        "name":repo_name,
        "description": "this is a simple app for TDS project 1",
        "private":False,
        "auto_init":False
    }
    response=requests.post(url,json=payload,headers=header)
    # response.raise_for_status()
    return {
        "repo_url":f"https://github.com/{github_username}/{repo_name}",
        "repo_name":repo_name
    }

def format_file_content(path: str, content: str) -> str:
    """Format file content based on file type"""
    try:
        # Remove any Windows style line endings
        content = content.replace('\r\n', '\n')
        
        if path.endswith('.json'):
            # Parse and format JSON files
            import json
            parsed = json.loads(content)
            return json.dumps(parsed, indent=2)
        
        elif path.endswith(('.js', '.jsx', '.ts', '.tsx', '.py', '.css', '.html')):
            # For code files, ensure proper line breaks
            # Remove multiple blank lines
            import re
            content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
            
            # Ensure content ends with single newline
            return content.rstrip() + '\n'
            
        elif path.endswith(('.md', '.txt')):
            # For text files, normalize line endings
            return content.rstrip() + '\n'
            
        else:
            # For unknown types, just normalize line endings
            return content.rstrip() + '\n'
    except Exception as e:
        print(f"Warning: Error formatting {path}: {e}")
        return content

def push(repo_name: str, files: dict, round:int):
    header = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }

    # First get existing file SHAs if round > 1
    existing_files = {}
    if round > 1:
        for path in files.keys():
            url = f"https://api.github.com/repos/{github_username}/{repo_name}/contents/{path}"
            response = requests.get(url, headers=header)
            if response.status_code == 200:
                existing_files[path] = response.json().get('sha')

    # Push each file
    for path, content in files.items():
        url = f"https://api.github.com/repos/{github_username}/{repo_name}/contents/{path}"
        
        # Format the content before encoding
        formatted_content = format_file_content(path, content)
        content_bytes = formatted_content.encode('utf-8')
        content_base64 = base64.b64encode(content_bytes).decode('utf-8')
        
        payload = {
            "message": f"Update file: {path}",
            "content": content_base64,
            "branch": "main"
        }

        # If this is an update (round > 1) and we have the file's SHA, include it
        if round > 1 and path in existing_files:
            payload["sha"] = existing_files[path]

        response = requests.put(url, json=payload, headers=header)
        if response.status_code not in [200, 201]:
            print(f"Error pushing {path}: {response.status_code} - {response.text}")
        response.raise_for_status()


    # fetch latest commit sha after uploading all files
    url =f"https://api.github.com/repos/{github_username}/{repo_name}/commits/main"
    header={
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"

    }
    response= requests.get(url, headers=header)
    sha= response.json().get('sha', '')
    return sha
    
    

def get_repo(repo_name:str):
    url=f"https://api.github.com/repos/{github_username}/{repo_name}/git/trees/main?recursive=1"
    header={
        "Authorization":f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    response=requests.get(url, headers=header)
    data=response.json().get('tree', [])
    files={}
    for file in data:
        if file.get('type') == "blob":
            path = file['path']
            file_url=f"https://api.github.com/repos/{github_username}/{repo_name}/contents/{path}"
            response=requests.get(file_url, headers=header)
            content_base64=response.json().get('content', '')
            content=base64.b64decode(content_base64).decode('utf-8') if content_base64 else ''
            files[path]=content
    return files



def github_page(repo_name: str):
    url= f"https://api.github.com/repos/{github_username}/{repo_name}/pages"
    header={
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.switcheroo-preview+json"
    }
    payload={
        "source":{
            "branch": "main",
            "path": "/"
        }
    }
    response = requests.post(url, json=payload, headers=header)
    if response.status_code not in [201, 409]:
       response.raise_for_status()
   
