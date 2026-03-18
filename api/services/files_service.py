from fastapi import UploadFile,HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from db.models import UserRecord, FileRecord, FileContentRecord
from pathlib import Path
from utils.files_utils import create_file_details, chunk_and_embed_by_file_type, embed

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
        chunks_data = chunk_and_embed_by_file_type(text_content, stored["content_type"])
        for chunk in chunks_data:
            content_record = FileContentRecord(
                file_id = db_file.id,
                chunk_content_tsv = func.to_tsvector("english", chunk["chunk_text"]),
                chunk_content_pv=chunk["embedding"]
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

def search_files_by_tsv_content(query_word: str, user_id: int, db: Session , limit: int = 20, offset: int = 0):
    query_word = (query_word or "").strip()
    if not query_word:
        return []
    
    tsquery = func.websearch_to_tsquery("english", query_word)
    rank = func.ts_rank_cd(FileContentRecord.chunk_content_tsv, tsquery).label("rank")

    chunks = (db.query(FileRecord, rank)
                .join(FileContentRecord, FileContentRecord.file_id == FileRecord.id)
                .filter(FileRecord.user_id == user_id)
                .filter(FileContentRecord.chunk_content_tsv.op("@@")(tsquery))
                .order_by(rank.desc(), FileRecord.created_at.desc())
                .offset(offset)
                .limit(limit)
                .all()
    )

     
    unique_results: list[dict] = []
    seen_file_ids = set()
    for file_record, file_rank in chunks:
        if file_record.id in seen_file_ids:
            continue
        seen_file_ids.add(file_record.id)
        unique_results.append(
            {
                "rank" : float(file_rank or 0.0),
                "file" : {
                    "id" : file_record.id ,
                    "original_name" : file_record.original_file_name,
                    "random_name" : file_record.file_name,
                    "content_type" : file_record.content_type,
                    "size" : file_record.size,
                    "user_id" : file_record.user_id,
                    "created_at" : file_record.created_at,
                    "path" : file_record.file_path
                },
            }
        )


    start = offset
    end = offset + limit
    return unique_results[start:end]

def search_files_by_embedded_content(query_word: str, user_id: int, db: Session , limit: int = 20, offset: int = 0):
    query_word = (query_word or "").strip()
    if not query_word:
        return []
    
    query_vector = embed([query_word])[0]
    rank = FileContentRecord.chunk_content_pv.cosine_distance(query_vector).label("distance")

    chunks = (db.query(FileRecord, rank)
                .join(FileContentRecord, FileContentRecord.file_id == FileRecord.id)
                .filter(FileRecord.user_id == user_id)
                .order_by(rank.asc()) 
                .limit(500) 
                .all()
    )
     
    unique_results: list[dict] = []
    seen_file_ids = set()
    for file_record, file_rank in chunks:
        if file_record.id in seen_file_ids:
            continue
        seen_file_ids.add(file_record.id)
        similarity = 1 - file_rank
        unique_results.append(
            {
                "rank" : float(similarity),
                "file" : {
                    "id" : file_record.id ,
                    "original_name" : file_record.original_file_name,
                    "random_name" : file_record.file_name,
                    "content_type" : file_record.content_type,
                    "size" : file_record.size,
                    "user_id" : file_record.user_id,
                    "created_at" : file_record.created_at,
                    "path" : file_record.file_path
                },
            }
        )


    start = offset
    end = offset + limit
    return unique_results[start:end]

