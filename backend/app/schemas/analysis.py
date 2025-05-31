from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
from app.models.analysis import AnalysisStatus, AnalysisType, VulnerabilityLevel

class AnalysisCreate(BaseModel):
    project_id: str
    analysis_type: AnalysisType = AnalysisType.SLITHER

class VulnerabilityResponse(BaseModel):
    id: str
    title: str
    description: str
    severity: VulnerabilityLevel
    impact: str
    recommendation: str
    code_snippet: Optional[str] = None
    references: List[str] = []

class AnalysisSummary(BaseModel):
    total: int
    high: int
    medium: int
    low: int
    informational: int

class AnalysisResponse(BaseModel):
    id: str
    project_id: str
    user_id: str
    analysis_type: AnalysisType
    status: AnalysisStatus
    
    # Results
    vulnerabilities: List[VulnerabilityResponse] = []
    summary: AnalysisSummary
    ai_recommendations: List[str] = []
    
    # Report
    report_available: bool = False
    
    # Error information
    error_message: Optional[str] = None
    
    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

class AnalysisReportResponse(BaseModel):
    analysis_id: str
    project_name: str
    report_content: str
    generated_at: datetime