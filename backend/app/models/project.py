from datetime import datetime, timezone
from typing import Optional
from beanie import Document
from pydantic import Field
from enum import Enum

class ProjectType(str, Enum):
    SINGLE_FILE = "single_file"
    FOUNDRY_PROJECT = "foundry_project"
    MIXED_PROJECT = "mixed_project"  

class ProjectStatus(str, Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class Project(Document):
    name: str
    description: Optional[str] = None
    user_id: str
    project_type: ProjectType
    status: ProjectStatus = ProjectStatus.UPLOADED
    
    # File information
    original_filename: str
    file_path: str
    file_size: int
    file_hash: str
    
    # Analysis results
    analysis_id: Optional[str] = None
    analysis_path: Optional[str] = None 
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Settings:
        collection = "projects"
        
    class Config:
        use_enum_values = True