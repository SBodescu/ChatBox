from fastapi import FastAPI, Depends, HTTPException, APIRouter
from api.services import auth_service
from api.schemas.users import UserCreate, UserLogin, UserResponse
from api.schemas.token import Token, TokenResponse
from db.database import get_db
from utils.jwt_token_utils import create_access_token

router = APIRouter(prefix = "/auth", tags = ["auth"])

@router.post("/login", response_model=Token)
def login(user: UserLogin, db = Depends(get_db)):
    try:
        user = auth_service.get_authenticate_user(user,db)
        user_access_token = create_access_token(data={"sub": str(user.id)})
        return Token(access_token=user_access_token)
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    

@router.post("/signup", response_model=TokenResponse)
def signup(user: UserCreate, db = Depends(get_db)):
    try:
        new_user = auth_service.create_user_account(user, db)
        user_access_token = create_access_token(data={"sub": str(new_user.id)})
        return TokenResponse(user = UserResponse.model_validate(new_user), token=Token(access_token=user_access_token))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))