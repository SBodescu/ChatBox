from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class FileResponse(BaseModel):
    id: int
    file_name: str
    file_path: str
    content_type: Optional[str] = None
    size: Optional[int] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
