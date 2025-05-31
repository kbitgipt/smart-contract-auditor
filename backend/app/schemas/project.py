from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.models.project import ProjectType, ProjectStatus

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)

class ProjectResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    user_id: str
    project_type: ProjectType
    status: ProjectStatus
    original_filename: str
    file_size: int
    analysis_id: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class UploadResponse(BaseModel):
    project: ProjectResponse
    message: str
    upload_success: bool