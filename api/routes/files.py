from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status, Query
from fastapi.responses import FileResponse as FastAPIFileResponse
from sqlalchemy.orm import Session

from db.models import UserRecord
from db.database import get_db
from api.services.auth_service import get_current_user
from api.schemas.files import FileResponse
from api.services import files_service 


router = APIRouter(prefix="/files", tags=["files"])

@router.post("", response_model = FileResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    current_user: UserRecord = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )
        
    saved_file = await files_service.create_file_record(
        file=file, 
        current_user=current_user, 
        db=db
    )
    return FileResponse.model_validate(saved_file)

@router.get("/search-hybrid")
def search_files(query_word: str, limit: int = 20, offset: int = 0,current_user: UserRecord = Depends(get_current_user), db: Session = Depends(get_db) ):
    query_word = (query_word or "").strip()
    if not query_word:
        raise HTTPException(status_code=400, detail="Query parameter is required")
    
    limit = max(1,min(limit,100))
    offset = max(0, offset)

    results = files_service.search_files_content_hybrid(query_word, current_user.id, db, limit, offset)
    return { "query": query_word,
            "limit" : limit,
            "offset" : offset,
            "results" : results
            }


@router.get("/search")
def search_files(query_word: str, limit: int = 20, offset: int = 0,current_user: UserRecord = Depends(get_current_user), db: Session = Depends(get_db) ):
    query_word = (query_word or "").strip()
    if not query_word:
        raise HTTPException(status_code=400, detail="Query parameter is required")
    
    limit = max(1,min(limit,100))
    offset = max(0, offset)

    results = files_service.search_files_by_tsv_content(query_word, current_user.id, db, limit, offset)
    return { "query": query_word,
            "limit" : limit,
            "offset" : offset,
            "results" : results
            }

@router.get("/search-embeddings")
def search_files(query_word: str, limit: int = 20, offset: int = 0,current_user: UserRecord = Depends(get_current_user), db: Session = Depends(get_db) ):
    query_word = (query_word or "").strip()
    if not query_word:
        raise HTTPException(status_code=400, detail="Query parameter is required")
    
    limit = max(1,min(limit,100))
    offset = max(0, offset)

    results = files_service.search_files_by_embedded_content(query_word, current_user.id, db, limit, offset)
    return { "query": query_word,
            "limit" : limit,
            "offset" : offset,
            "results" : results
            }

@router.get("/{file_id}", response_model=FileResponse)
def get_file(file_id: int, current_user: UserRecord = Depends(get_current_user), db: Session = Depends(get_db)):
    db_file = files_service.get_file_by_id(file_id, current_user.id, db)
    if not db_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Filename not found"
        )
        
    return FileResponse.model_validate(db_file)


@router.get("", response_model=list[FileResponse])
def get_files_by_user_id(current_user: UserRecord = Depends(get_current_user),db: Session = Depends(get_db)):
    db_files = files_service.get_files_for_user(current_user.id, db)
    
    return [FileResponse.model_validate(f) for f in db_files]

@router.get("/{file_id}/content", response_class=FastAPIFileResponse)
async def get_file_content(file_id: int, current_user: UserRecord = Depends(get_current_user), db: Session = Depends(get_db) ):
    content_type, original_file_name, file_path = files_service.get_file_record_by_id(file_id, current_user.id, db)
    return FastAPIFileResponse(path=file_path,media_type=content_type, filename=original_file_name)

@router.delete("/{file_id}")
def remove_file_by_id(file_id: int, current_user: UserRecord = Depends(get_current_user), db: Session = Depends(get_db)):
    db_file = files_service.get_file_by_id(file_id, current_user.id, db)
    if not db_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Filename not found"
        )
    db.delete(db_file)
    db.commit()
  
    return f"File with name:{db_file.file_name} removed"


    