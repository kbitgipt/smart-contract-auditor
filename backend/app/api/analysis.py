from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from typing import List
from app.models.user import User
from app.models.project import Project, ProjectStatus, ProjectType
from app.models.analysis import Analysis, AnalysisStatus
from app.schemas.analysis import AnalysisCreate, AnalysisResponse, AnalysisReportResponse, VulnerabilityResponse, AnalysisSummary
from app.services.analysis_service import AnalysisService
from app.api.auth import get_current_user_dependency
import asyncio
from pathlib import Path

router = APIRouter()

@router.post("/analyze/{project_id}", response_model=AnalysisResponse)
async def start_analysis(
    project_id: str,
    current_user: User = Depends(get_current_user_dependency)
):
    """Start automatic analysis for normal users (single file only)"""
    
    # Get project
    project = await Project.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check ownership
    if project.user_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Check if project is single file (normal users only)
    if current_user.mode != "auditor" and project.project_type != ProjectType.SINGLE_FILE:
        raise HTTPException(
            status_code=400, 
            detail="Normal users can only analyze single .sol files"
        )
    
    # Check if already analyzing
    if project.status == ProjectStatus.PROCESSING:
        raise HTTPException(status_code=400, detail="Analysis already in progress")
    
    # Check if analysis already exists and completed
    if project.analysis_id:
        existing_analysis = await Analysis.get(project.analysis_id)
        if existing_analysis and existing_analysis.status == AnalysisStatus.COMPLETED:
            return await _format_analysis_response(existing_analysis)
    
    try:
        # Start analysis in background
        analysis_service = AnalysisService()
        
        # For demo purposes, we'll run synchronously
        # In production, use Celery or similar for background tasks
        analysis = await analysis_service.perform_full_analysis(project)
        
        return await _format_analysis_response(analysis)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )

@router.get("/analysis/{analysis_id}", response_model=AnalysisResponse)
async def get_analysis(
    analysis_id: str,
    current_user: User = Depends(get_current_user_dependency)
):
    """Get analysis results"""
    
    analysis = await Analysis.get(analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    # Check ownership
    if analysis.user_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    return await _format_analysis_response(analysis)

@router.get("/analysis/{analysis_id}/report", response_class=HTMLResponse)
async def get_analysis_report(
    analysis_id: str,
    current_user: User = Depends(get_current_user_dependency)
):
    """Get HTML report for analysis"""
    
    analysis = await Analysis.get(analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    # Check ownership
    if analysis.user_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    if analysis.status != AnalysisStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Analysis not completed yet")
    
    if not analysis.report_path or not Path(analysis.report_path).exists():
        raise HTTPException(status_code=404, detail="Report not found")
    
    # Read and return HTML report
    with open(analysis.report_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    return HTMLResponse(content=html_content)

@router.get("/project/{project_id}/analyses", response_model=List[AnalysisResponse])
async def get_project_analyses(
    project_id: str,
    current_user: User = Depends(get_current_user_dependency)
):
    """Get all analyses for a project"""
    
    project = await Project.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check ownership
    if project.user_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    analyses = await Analysis.find(Analysis.project_id == project_id).to_list()
    
    return [await _format_analysis_response(analysis) for analysis in analyses]

async def _format_analysis_response(analysis: Analysis) -> AnalysisResponse:
    """Format analysis data for API response"""
    
    vulnerabilities = []
    summary = AnalysisSummary(total=0, high=0, medium=0, low=0, informational=0)
    ai_recommendations = []
    
    # Extract data from AI analysis
    if analysis.ai_analysis:
        ai_vulns = analysis.ai_analysis.get("vulnerabilities", [])
        for vuln in ai_vulns:
            vulnerabilities.append(VulnerabilityResponse(
                id=vuln.get("id", "unknown"),
                title=vuln.get("title", "Unknown Issue"),
                description=vuln.get("description", ""),
                severity=vuln.get("severity", "informational").lower(),
                impact=vuln.get("impact", ""),
                recommendation=vuln.get("recommendation", ""),
                code_snippet=vuln.get("code_snippet"),
                references=vuln.get("references", [])
            ))
        
        ai_summary = analysis.ai_analysis.get("summary", {})
        summary = AnalysisSummary(
            total=ai_summary.get("total", 0),
            high=ai_summary.get("high", 0),
            medium=ai_summary.get("medium", 0),
            low=ai_summary.get("low", 0),
            informational=ai_summary.get("informational", 0)
        )
        
        ai_recommendations = analysis.ai_analysis.get("ai_recommendations", [])
    
    return AnalysisResponse(
        id=str(analysis.id),
        project_id=analysis.project_id,
        user_id=analysis.user_id,
        analysis_type=analysis.analysis_type,
        status=analysis.status,
        vulnerabilities=vulnerabilities,
        summary=summary,
        ai_recommendations=ai_recommendations,
        report_available=bool(analysis.report_path and Path(analysis.report_path).exists()),
        error_message=analysis.error_message,
        started_at=analysis.started_at,
        completed_at=analysis.completed_at,
        created_at=analysis.created_at
    )