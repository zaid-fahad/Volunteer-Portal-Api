import secrets
import string
import re

# random password creation

def create_random_password() -> str :
    return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(10))

def drive_to_img_src(url: str) -> str:
    if not url :
        return None
    
    patterns = [
        r"id=([^&]+)",
        r"/file/d/([^/]+)",
        r"uc\?id=([^&]+)"
    ]

    for p in patterns:
        match = re.search(p, url)
        if match:
            file_id = match.group(1)
            return f"https://drive.google.com/uc?export=view&id={file_id}"

    raise ValueError("Invalid Google Drive URL")