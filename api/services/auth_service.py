from db.model import UserRecord
from fastapi import Depends,HTTPException, status
from sqlalchemy.orm import Session
from api.schemas.users import  UserCreate, UserLogin
from utils.password_utils import get_hash_password
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from db.database import get_db
from utils.jwt_token_utils import SECRET_KEY, ALGORITHM
from utils.password_utils import verify_password


security = HTTPBearer(auto_error=False)

def get_authenticate_user(user: UserLogin, db: Session):
    auth_user = db.query(UserRecord).filter(UserRecord.email == user.email).first()
    if not auth_user or not verify_password(user.password,auth_user.password_hash):
        return None
    return auth_user

def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(security), db: Session = Depends(get_db)) -> UserRecord:
    if not credentials or credentials.scheme != "Bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization",
        )
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        user_id = int(user_id)
    except (JWTError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = db.query(UserRecord).filter(UserRecord.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user

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
    
