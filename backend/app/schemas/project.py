from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.models.project import ProjectType, ProjectStatus

# class ProjectCreate(BaseModel):
#     name: str = Field(..., min_length=1, max_length=100)
#     description: Optional[str] = Field(None, max_length=500)

class ProjectResponse(BaseModel):
    id: str
    name: str
    original_filename: str
    project_type: ProjectType
    status: ProjectStatus
    file_size: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    description: Optional[str]
    analysis_id: Optional[str]
    user_id: str
    description: Optional[str] = None

    class Config:
        from_attributes = True

class ProjectDetailResponse(ProjectResponse):
    file_path: str
    # user_id: str

    class Config:
        from_attributes = True

class ProjectSourceResponse(BaseModel):
    project_id: str
    file_path: Optional[str] = None
    source_code: Optional[str] = None
    project_type: ProjectType
    available_files: Optional[List[str]] = None

class UploadResponse(BaseModel):
    project: ProjectResponse
    message: str
    upload_success: bool