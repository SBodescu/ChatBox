from pydantic import BaseModel
from api.schemas.users import UserResponse

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenResponse(BaseModel):
    user: UserResponse
    token: Token