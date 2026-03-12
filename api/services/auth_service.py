from db.model import UserRecord
from fastapi import Depends
from sqlalchemy.orm import Session
from api.schemas.users import UserResponse, UserCreate, UserLogin
from passlib.context import CryptContext
from db.database import get_db
from api.config import settings
from datetime import datetime, timedelta, timezone
import jwt

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def authenticate_user(user: UserLogin, db: Session):
    auth_user = db.query(UserRecord).filter(UserRecord.email == user.email).first()
    if not auth_user or not verify_password(user.password,auth_user.password_hash):
        return None
    return auth_user

def create_user_account(user: UserCreate, db: Session):
    existing_user = db.query(UserRecord).filter(UserRecord.email == user.email).first()

    if existing_user:
        raise ValueError("Emailul este deja înregistrat")
    
    hash_pass = get_hash_password(user.password)

    new_user = UserRecord(
        email=user.email,
        name=user.name,
        phone=user.phone,
        password_hash=hash_pass
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user
    
