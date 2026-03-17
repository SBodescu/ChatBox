from fastapi import UploadFile,HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from db.models import UserRecord, FileRecord, FileContentRecord
from pathlib import Path
from utils.files_utils import create_file_details

async def store_file(file: UploadFile,current_user: UserRecord):
    original_file_name, file_name, dir_path = create_file_details(current_user.id, file)

    content = await file.read()
    dir_path.write_bytes(content)

    return {
        "filename": original_file_name,
        "generated_file_name": file_name,
        "content_type": file.content_type or "application/octet-stream",
        "size": len(content),
        "path": str(dir_path),
        "raw_bytes": content,
    }


async def create_file_record(file: UploadFile, current_user: UserRecord, db: Session):
    stored =  await store_file(file,current_user)

    db_file = FileRecord(
        user_id=current_user.id,
        original_file_name = stored["filename"],
        file_name=stored["generated_file_name"],
        file_path= stored["path"],
        content_type=stored["content_type"],
        size=stored["size"]
    )

    db.add(db_file)
    db.commit()
    db.refresh(db_file)

    raw_bytes = stored.get("raw_bytes", b"")
    try:
        text_content = raw_bytes.decode("utf-8", errors="ignore")
    except Exception:
        text_content = ""
    if text_content:
        content_record = FileContentRecord(
            file_id = db_file.id,
            content_tsv = func.to_tsvector("english", text_content),
        )
        db.add(content_record)

    db.commit()
    db.refresh(db_file)

    return db_file

def get_files_for_user(user_id: int, db: Session):
   return db.query(FileRecord).filter(FileRecord.user_id == user_id).all()

def get_file_by_id(file_id: int,user_id: int,  db: Session):
    return db.query(FileRecord).filter(FileRecord.id == file_id, FileRecord.user_id == user_id).first()

def get_file_record_by_id(file_id: int,user_id: int,  db: Session):
    db_file = get_file_by_id(file_id, user_id, db)
    file_path = Path(db_file.file_path)
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")
    return [db_file.content_type, db_file.original_file_name, file_path]

def search_files_by_content(query_word: str, user_id: int, db: Session):
    file_ids = db.query(FileContentRecord.file_id).join(
        FileRecord, FileContentRecord.file_id == FileRecord.id
    ).filter(
        FileRecord.user_id == user_id,
        FileContentRecord.content_tsv.match(query_word) 
    ).all()
    return [file.file_id for file in file_ids]