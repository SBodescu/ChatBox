from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from db.database import Base, engine, get_db
from db.model import UserRecord
from schemas.users import UserResponse, UserCreate
import uvicorn

app = FastAPI()

Base.metadata.create_all(bind=engine)

@app.get("/")
def read_root():
    return {"Hello": "super"}

@app.post("/users", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(UserRecord).filter(UserRecord.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    new_user = UserRecord(
        email=user.email,
        name=user.name,
        phone=user.phone,
        password_hash=user.password
    )
  
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user

@app.get("/users",response_model=list[UserResponse])
def get_users(db: Session = Depends(get_db)):
    users = db.query(UserRecord).all()
    return users

@app.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(UserRecord).filter(UserRecord.id == user_id ).first()
    if user is None:
        raise HTTPException(status_code=404, detail="Utilizatorul nu a fost găsit")
    return user

@app.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(UserRecord).filter(UserRecord.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="Utilizatorul nu a fost găsit")
    db.delete(user)
    db.commit()
    return f"User with id:{user_id} has been deleted from database"

def main():
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
