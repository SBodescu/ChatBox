from pathlib import Path

from fastapi import File, UploadFile
import uuid


UPLOAD_DIR = Path("files")

def generate_file_name(file_name: str):
    
    unique_id = uuid.uuid4().hex
    
    path_obj = Path(file_name)
    base_name = path_obj.stem
    extension = path_obj.suffix
    
    return f"{base_name}_{unique_id}{extension}"

def create_file_details(user_id: int,file: UploadFile = File(...)):
    safe_name = Path(file.filename).name
    generated_name = generate_file_name(safe_name)
    user_dir = UPLOAD_DIR / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    dest = user_dir / generated_name

    return safe_name,generated_name,dest


