from datetime import datetime
from typing import Optional, List, Dict, Any
from beanie import Document
from pydantic import Field
from enum import Enum

class AnalysisStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running" 
    COMPLETED = "completed"
    FAILED = "failed"

class AnalysisType(str, Enum):
    SLITHER = "slither"
    FOUNDRY = "foundry"
    COMBINED = "combined"

class VulnerabilityLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"

class Analysis(Document):
    project_id: str
    user_id: str
    analysis_type: AnalysisType
    status: AnalysisStatus = AnalysisStatus.PENDING
    
    # Results
    slither_results: Optional[Dict[str, Any]] = None
    ai_analysis: Optional[Dict[str, Any]] = None
    report_path: Optional[str] = None
    
    # Additional report paths for different formats
    json_report_path: Optional[str] = None
    markdown_report_path: Optional[str] = None
    
    # Error information
    error_message: Optional[str] = None
    
    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    created_at: datetime = Field(default_factory=datetime.now(datetime.timezone.utc))
    updated_at: datetime = Field(default_factory=datetime.now(datetime.timezone.utc))
    
    class Settings:
        collection = "analyses"
        
    class Config:
        use_enum_values = True