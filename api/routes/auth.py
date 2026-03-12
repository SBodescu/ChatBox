from fastapi import FastAPI, Depends, HTTPException, APIRouter
from sqlalchemy.orm import Session
from db.model import UserRecord
from api.services import auth_service
from api.schemas.users import UserResponse, UserCreate, UserLogin
from api.schemas.token import Token, TokenResponse
from db.database import get_db

router = APIRouter(prefix = "/auth", tags = ["auth"])

@router.post("/login", response_model=Token)
def login(user: UserLogin, db = Depends(get_db)):
    try:
        user = auth_service.authenticate_user(user,db)
        access_token = auth_service.create_access_token(data={"sub": str(user.id)})
        return {
            "access_token": access_token, 
            "token_type": "bearer"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    

@router.post("/signup", response_model=TokenResponse)
def signup(user: UserCreate, db = Depends(get_db)):
    try:
        new_user = auth_service.create_user_account(user, db)
        user_access_token = auth_service.create_access_token(data={"sub": str(new_user.id)})
        return {
            "user": new_user,
            "token":{
                "access_token": user_access_token,
                "token_type": "bearer"
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))