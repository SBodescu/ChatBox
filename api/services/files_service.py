from fastapi import UploadFile,HTTPException
from sqlalchemy.orm import Session
from db.models import UserRecord, FileRecord
from pathlib import Path
from utils.files_utils import create_file_details

async def create_file_record(file: UploadFile, current_user: UserRecord, db: Session):

    original_file_name, file_name, dir_path = create_file_details(current_user.id, file)

    content = await file.read()
    dir_path.write_bytes(content)

    db_file = FileRecord(
        user_id=current_user.id,
        original_file_name = original_file_name,
        file_name=file_name,
        file_path=str(dir_path),
        content_type=file.content_type or "application/octet-stream",
        size=len(content)
    )

    db.add(db_file)
    db.commit()
    db.refresh(db_file)

    return db_file

def get_files_for_user(user_id: int, db: Session):
   return db.query(FileRecord).filter(FileRecord.user_id == user_id).all()

def get_file_by_id(file_id: int,user_id: int,  db: Session):
    return db.query(FileRecord).filter(FileRecord.id == file_id, FileRecord.user_id == user_id).first()

def get_file_content_by_id(file_id: int,user_id: int,  db: Session):
    db_file = get_file_by_id(file_id, user_id, db)
    file_path = Path(db_file.file_path)
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")
    return [db_file.content_type, db_file.original_file_name, file_path]