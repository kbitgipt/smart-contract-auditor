from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from typing import List, Optional, Dict
from app.models.user import User
from app.models.project import Project, ProjectStatus, ProjectType
from app.models.analysis import Analysis, AnalysisStatus
from app.schemas.analysis import AnalysisResponse, VulnerabilityResponse, AnalysisSummary
from app.services.analysis_service import AnalysisService
from app.services.static_analyzer import SlitherOptions, StaticAnalyzer
from app.api.auth import get_current_user_dependency
from pathlib import Path
from pydantic import BaseModel
from datetime import datetime, timezone

router = APIRouter(tags=["Analysis"])

# === AUDITOR HELPER APIs ===

@router.get("/detectors")
async def get_available_detectors(
    current_user: User = Depends(get_current_user_dependency)
):
    """Get available Slither detectors for auditors"""
    if current_user.mode != "auditor":
        raise HTTPException(
            status_code=403, 
            detail="Detector information requires auditor mode"
        )
    
    analyzer = StaticAnalyzer()
    return {
        "available_detectors": analyzer.get_available_detectors(),
        "detector_categories": analyzer.get_detector_categories()
    }

# === PROJECT-SPECIFIC ROUTES ===
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

# === AUDITOR STEP-BY-STEP ANALYSIS APIs ===

class StaticAnalysisRequest(BaseModel):
    """Request for static analysis step"""
    slither_options: Optional[SlitherOptions] = None

@router.post("/analyze/{project_id}/static", response_model=AnalysisResponse)
async def perform_static_analysis(
    project_id: str,
    request: StaticAnalysisRequest,
    current_user: User = Depends(get_current_user_dependency)
):
    """Static analysis for single .sol files (auditors only)"""
    
    if current_user.mode != "auditor":
        raise HTTPException(status_code=403, detail="Requires auditor mode")
    
    project = await Project.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if project.user_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    if project.status == ProjectStatus.PROCESSING:
        raise HTTPException(status_code=400, detail="Analysis already in progress")
    
    if project.project_type != ProjectType.SINGLE_FILE:
        raise HTTPException(
            status_code=400, 
            detail="This endpoint is for single file projects. Use /foundry for Foundry projects."
        )

    try:
        analysis_service = AnalysisService()
        analysis = await analysis_service._perform_single_file_static_analysis(
            project, 
            request.slither_options
        )
        
        return await _format_analysis_response(analysis)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Static analysis failed: {str(e)}")

class FoundryAnalysisRequest(BaseModel):
    """Request for Foundry project analysis"""
    target_files: Optional[List[str]] = None
    detectors: Optional[List[str]] = None
    exclude_detectors: Optional[List[str]] = None
    exclude_dependencies: bool = True
    exclude_tests: bool = True
    exclude_informational: bool = False
    exclude_low: bool = False

@router.post("/analyze/{project_id}/foundry", response_model=AnalysisResponse)
async def perform_foundry_analysis(
    project_id: str,
    request: FoundryAnalysisRequest,
    current_user: User = Depends(get_current_user_dependency)
):
    """Static analysis for Foundry projects endpoint (auditors only)"""
    
    if current_user.mode != "auditor":
        raise HTTPException(status_code=403, detail="Requires auditor mode")
    
    project = await Project.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if project.user_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    if project.project_type != ProjectType.FOUNDRY_PROJECT:
        raise HTTPException(
            status_code=400, 
            detail="This endpoint is for Foundry projects. Use /static for single files."
        )
    
    try:
        slither_options = SlitherOptions(
            target_files=request.target_files,
            detectors=request.detectors,
            exclude_detectors=request.exclude_detectors,
            exclude_dependencies=request.exclude_dependencies,
            exclude_informational=request.exclude_informational,
            exclude_low=request.exclude_low
        )
        
        analysis_service = AnalysisService()
        analysis = await analysis_service.perform_foundry_static_analysis(
            project, slither_options
        )
        
        return await _format_analysis_response(analysis)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Foundry analysis failed: {str(e)}")

@router.post("/analyze/{analysis_id}/ai-enhance", response_model=AnalysisResponse)
async def perform_ai_enhancement(
    analysis_id: str,
    current_user: User = Depends(get_current_user_dependency)
):
    """Step 2: Enhance analysis with AI (for auditors)"""
    
    # Check if user is auditor
    if current_user.mode != "auditor":
        raise HTTPException(
            status_code=403, 
            detail="AI enhancement requires auditor mode"
        )
    
    # Get analysis
    analysis = await Analysis.get(analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    if analysis.user_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Check if static analysis is completed
    if analysis.status != AnalysisStatus.COMPLETED or not analysis.slither_results:
        raise HTTPException(
            status_code=400, 
            detail="Static analysis must be completed first"
        )
    
    try:
        analysis_service = AnalysisService()
        enhanced_analysis = await analysis_service.perform_ai_enhancement(analysis)
        
        return await _format_analysis_response(enhanced_analysis)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"AI enhancement failed: {str(e)}"
        )

@router.post("/project/{project_id}/query")
async def query_project_context(
    project_id: str,
    question: str,
    current_user: User = Depends(get_current_user_dependency)
):
    """Query project context using AI with vector store"""
    project = await Project.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check ownership
    if project.user_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        analysis_service = AnalysisService()
        result = await analysis_service.ai_analyzer.query_project_context(project_id, question)
        
        if result["success"]:
            return {"response": result["response"]}
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

class ReportGenerationRequest(BaseModel):
    """Request for report generation"""
    format_type: str = "html"  # html, json, markdown

@router.post("/analyze/{analysis_id}/generate-report")
async def generate_report(
    analysis_id: str,
    request: ReportGenerationRequest,
    current_user: User = Depends(get_current_user_dependency)
):
    """Step 3: Generate report (for auditors)"""
    
    # Check if user is auditor
    if current_user.mode != "auditor":
        raise HTTPException(
            status_code=403, 
            detail="Report generation requires auditor mode"
        )
    
    # Get analysis
    analysis = await Analysis.get(analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    if analysis.user_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Check if analysis has data
    if not analysis.ai_analysis:
        raise HTTPException(
            status_code=400, 
            detail="No analysis data available for report generation"
        )
    
    try:
        project = await Project.get(analysis.project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # print(f"🔍 Project data for report generation:")
        # print(f"  - ID: {project.id}")
        # print(f"  - Name: {project.name}")
        # print(f"  - Project type: {project.project_type} (type: {type(project.project_type)})")
        
        analysis_service = AnalysisService()
        report_path = await analysis_service.generate_analysis_report(
            analysis, 
            request.format_type
        )
        
        return {
            "success": True,
            "message": "Report generated successfully",
            "report_path": report_path,
            "format": request.format_type,
            "download_url": f"/api/analysis/{analysis_id}/report"
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        
        raise HTTPException(
            status_code=500,
            detail=f"Report generation failed: {str(e)}"
        )

# === ANALYSIS-SPECIFIC ROUTES ===

@router.get("/{analysis_id}/static-results")
async def get_static_analysis_results(
    analysis_id: str,
    current_user: User = Depends(get_current_user_dependency)
):
    """Get raw static analysis results for auditor review"""

    if current_user.mode != "auditor":
        raise HTTPException(
            status_code=403, 
            detail="Static results access requires auditor mode"
        )
    
    # Return both raw and parsed results
    try:
        # Try to fetch analysis with better error handling
        # from bson import ObjectId
        # Check if analysis_id is valid ObjectId format
        # if not ObjectId.is_valid(analysis_id):
        #     print(f"❌ Invalid ObjectId format: {analysis_id}")
        #     raise HTTPException(status_code=400, detail="Invalid analysis ID format")
        
        analysis = await Analysis.get(analysis_id)

        if not analysis:
            # print(f"❌ Analysis not found with ID: {analysis_id}")
            # # List all analyses for this user for debugging
            # user_analyses = await Analysis.find(Analysis.user_id == str(current_user.id)).to_list()
            # print(f"📋 User has {len(user_analyses)} analyses:")
            # for ua in user_analyses:
            #     print(f"  - {ua.id} (status: {ua.status})")

            raise HTTPException(status_code=404, detail="Analysis not found")
        
        if analysis.user_id != str(current_user.id):
            raise HTTPException(status_code=403, detail="Access denied") 

        if not analysis.slither_results:
            raise HTTPException(status_code=404, detail="No static analysis results found")
            
        parsed_results = analysis.ai_analysis or {
            "vulnerabilities": [],
            "summary": {"total": 0, "high": 0, "medium": 0, "low": 0, "informational": 0},
            "raw_findings": []
        }
            
        result = {
                "analysis_id": analysis_id,
                "slither_results": analysis.slither_results,
                "parsed_results": parsed_results,
                "status": analysis.status,
                "completed_at": analysis.completed_at
            }
        return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error returning static results: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve static results: {str(e)}"
        )    
    # return {
    #     "analysis_id": analysis_id,
    #     "slither_results": analysis.slither_results,
    #     "parsed_results": analysis.ai_analysis if not analysis.ai_analysis.get("ai_recommendations") else analysis.ai_analysis.get("static_findings", []),
    #     "status": analysis.status,
    #     "completed_at": analysis.completed_at
    # }

@router.put("/{analysis_id}/modify-results")
async def modify_analysis_results(
    analysis_id: str,
    modified_data: Dict,
    current_user: User = Depends(get_current_user_dependency)
):
    """Allow auditor to modify analysis results before AI enhancement"""
    
    if current_user.mode != "auditor":
        raise HTTPException(
            status_code=403, 
            detail="Result modification requires auditor mode"
        )
    
    analysis = await Analysis.get(analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    if analysis.user_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        # Validate modified data structure
        if not _validate_modification_data(modified_data):
            raise HTTPException(
                status_code=400, 
                detail="Invalid modification data structure"
            )
        
        # Create backup of original data
        if not analysis.ai_analysis:
            analysis.ai_analysis = {}
        
        # Store original parsed results as backup if not exists
        if "original_parsed_results" not in analysis.ai_analysis:
            static_analyzer = StaticAnalyzer()
            original_parsed = static_analyzer.parse_slither_results(analysis.slither_results)
            analysis.ai_analysis["original_parsed_results"] = original_parsed

        # Update with modified data
        analysis.ai_analysis.update({
            "vulnerabilities": modified_data.get("vulnerabilities", []),
            "summary": modified_data.get("summary", {}),
            "modification_metadata": {
                "modified_by": str(current_user.id),
                "modified_at": datetime.now(timezone.utc).isoformat(),
                "modification_note": modified_data.get("modification_note", ""),
                "changes_summary": _generate_changes_summary(
                    analysis.ai_analysis.get("original_parsed_results", {}),
                    modified_data
                )
            },
            "status": "modified_by_auditor"
        })
        
        await analysis.save()
        
        return {
            "success": True,
            "message": "Analysis results modified successfully",
            "changes_summary": analysis.ai_analysis["modification_metadata"]["changes_summary"],
            "modified_analysis": await _format_analysis_response(analysis)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to modify results: {str(e)}"
        )

@router.post("/{analysis_id}/reset-modifications")
async def reset_modifications(
    analysis_id: str,
    current_user: User = Depends(get_current_user_dependency)
):
    """Reset modifications and restore original parsed results"""
    
    if current_user.mode != "auditor":
        raise HTTPException(status_code=403, detail="Requires auditor mode")
    
    analysis = await Analysis.get(analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    if analysis.user_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        if not analysis.ai_analysis or "original_parsed_results" not in analysis.ai_analysis:
            # Re-parse from slither results
            static_analyzer = StaticAnalyzer()
            original_parsed = static_analyzer.parse_slither_results(analysis.slither_results)
        else:
            original_parsed = analysis.ai_analysis["original_parsed_results"]
        
        # Restore original data
        analysis.ai_analysis.update({
            "vulnerabilities": original_parsed.get("vulnerabilities", []),
            "summary": original_parsed.get("summary", {}),
            "status": "original_restored",
            "restored_at": datetime.now(timezone.utc).isoformat()
        })
        
        await analysis.save()
        
        return {
            "success": True,
            "message": "Original results restored successfully",
            "restored_analysis": await _format_analysis_response(analysis)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reset modifications: {str(e)}"
        )

# Validate modification data structure
def _validate_modification_data(data: Dict) -> bool:
    """Validate modification data structure"""
    required_fields = ["vulnerabilities", "summary"]
    if not all(field in data for field in required_fields):
        return False
        
    # Validate vulnerabilities structure
    if not isinstance(data["vulnerabilities"], list):
        return False
        
    for vuln in data["vulnerabilities"]:
        if not isinstance(vuln, dict):
            return False
        required_vuln_fields = ["id", "title", "severity", "description"]
        if not all(field in vuln for field in required_vuln_fields):
            return False
            
    # Validate summary structure
    summary = data["summary"]
    if not isinstance(summary, dict):
        return False
    required_summary_fields = ["total", "high", "medium", "low", "informational"]
    if not all(field in summary for field in required_summary_fields):
        return False
        
    return True

def _generate_changes_summary(original: Dict, modified: Dict) -> Dict:
    """Generate summary of changes made"""
    original_vulns = original.get("vulnerabilities", [])
    modified_vulns = modified.get("vulnerabilities", [])
    
    original_ids = {v["id"] for v in original_vulns}
    modified_ids = {v["id"] for v in modified_vulns}
    
    return {
        "vulnerabilities_added": len(modified_ids - original_ids),
        "vulnerabilities_removed": len(original_ids - modified_ids),
        "vulnerabilities_modified": len([
            v for v in modified_vulns 
            if v["id"] in original_ids and v != next(
                (ov for ov in original_vulns if ov["id"] == v["id"]), {}
            )
        ]),
        "summary_changed": original.get("summary") != modified.get("summary"),
        "total_original": len(original_vulns),
        "total_modified": len(modified_vulns)
    }

@router.get("/{analysis_id}/report", response_class=HTMLResponse)
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

@router.get("/{analysis_id}/project-structure")
async def get_project_structure(
    analysis_id: str,
    current_user: User = Depends(get_current_user_dependency)
):
    """Get Foundry project structure for analysis"""
    
    if current_user.mode != "auditor":
        raise HTTPException(
            status_code=403, 
            detail="Project structure access requires auditor mode"
        )
    
    analysis = await Analysis.get(analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    if analysis.user_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get project
    project = await Project.get(analysis.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if project.project_type == ProjectType.FOUNDRY_PROJECT:
        from app.services.file_service import FileService
        
        project_path = Path(project.file_path)
        if not project_path.exists():
            raise HTTPException(status_code=404, detail="Project path not found")
        
        structure = FileService.analyze_foundry_project_structure(project_path)
        
        return {
            "analysis_id": analysis_id,
            "project_type": "foundry",
            "structure": structure,
            "metadata": analysis.ai_analysis.get("foundry_metadata", {}) if analysis.ai_analysis else {}
        }
    else:
        # Single file project
        return {
            "analysis_id": analysis_id,
            "project_type": "single_file",
            "structure": {
                "source_files": [project.original_filename],
                "is_foundry": False
            }
        }

# === NORMAL ANALYSIS APIs ===

@router.post("/analyze/{project_id}", response_model=AnalysisResponse)
async def auto_analysis(
    project_id: str,
    current_user: User = Depends(get_current_user_dependency)
):
    """Start automatic analysis for normal users"""
    
    # Get project
    project = await Project.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check ownership
    if project.user_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # normal users only
    if current_user.mode == "auditor":
        raise HTTPException(
            status_code=400, 
            detail="Normal users only. Auditors should use step-by-step analysis."
    )
    
    # Check if already analyzing
    if project.status == ProjectStatus.PROCESSING:
        raise HTTPException(status_code=400, detail="Analysis already in progress")
    
    # Check if analysis already exists and completed
    # if project.analysis_id:
    #     existing_analysis = await Analysis.get(project.analysis_id)
    #     if existing_analysis and existing_analysis.status == AnalysisStatus.COMPLETED:
    #         return await _format_analysis_response(existing_analysis)
    
    try:
        analysis_service = AnalysisService()
        
        analysis = await analysis_service.perform_full_analysis(project)

        response = await _format_analysis_response(analysis)

        return response
        
    except Exception as e:
        import traceback
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )

# GENERIC ROUTE - MUST BE LAST
@router.get("/{analysis_id}", response_model=AnalysisResponse)
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

