from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from typing import Optional, List
from pathlib import Path
from datetime import datetime
from app.models.user import User
from app.models.project import Project, ProjectType, ProjectStatus
from app.schemas.project import ProjectCreate, UploadResponse, ProjectResponse
from app.services.file_service import FileService
from app.api.auth import get_current_user_dependency

router = APIRouter()

@router.post("/", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user_dependency)
):
    """Upload smart contract file or project"""
    
    try:
        print(f"Received upload request from user: {current_user.email}")
        print(f"File: {file.filename}, Size: {file.size}")
        print(f"Project name: {name}")

        # Validate file
        FileService.validate_file(file)
        
        # Save file
        file_path, file_size, file_hash = await FileService.save_upload_file(file, str(current_user.id))
        
        # Detect project type
        project_type_str, analysis_path = FileService.detect_project_type(file_path)
        project_type = ProjectType.SINGLE_FILE if project_type_str == "single_file" else ProjectType.FOUNDRY_PROJECT
        
        # Create project record
        project = Project(
            name=name,
            description=description,
            user_id=str(current_user.id),
            project_type=project_type,
            status=ProjectStatus.UPLOADED,
            original_filename=file.filename,
            file_path=str(file_path),
            file_size=file_size,
            file_hash=file_hash
        )
        
        print("Inserting project to database...")
        await project.insert()
        print(f"Project created with ID: {project.id}")
        
        return UploadResponse(
            project=ProjectResponse(
                id=str(project.id),
                name=project.name,
                description=project.description,
                user_id=project.user_id,
                project_type=project.project_type,
                status=project.status,
                original_filename=project.original_filename,
                file_size=project.file_size,
                analysis_id=project.analysis_id,
                created_at=project.created_at,
                updated_at=project.updated_at
            ),
            message="File uploaded successfully",
            upload_success=True
        )
        
    except HTTPException:
        print(f"HTTP Exception: {e.detail}")
        raise
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Upload failed: {str(e)}"
        )

@router.get("/projects", response_model=List[ProjectResponse])
async def get_user_projects(
    current_user: User = Depends(get_current_user_dependency)
):
    """Get all projects for current user"""
    projects = await Project.find(Project.user_id == str(current_user.id)).to_list()
    
    return [
        ProjectResponse(
            id=str(project.id),
            name=project.name,
            description=project.description,
            user_id=project.user_id,
            project_type=project.project_type,
            status=project.status,
            original_filename=project.original_filename,
            file_size=project.file_size,
            analysis_id=project.analysis_id,
            created_at=project.created_at,
            updated_at=project.updated_at
        )
        for project in projects
    ]

@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    current_user: User = Depends(get_current_user_dependency)
):
    """Get specific project"""
    project = await Project.get(project_id)
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check ownership
    if project.user_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    return ProjectResponse(
        id=str(project.id),
        name=project.name,
        description=project.description,
        user_id=project.user_id,
        project_type=project.project_type,
        status=project.status,
        original_filename=project.original_filename,
        file_size=project.file_size,
        analysis_id=project.analysis_id,
        created_at=project.created_at,
        updated_at=project.updated_at
    )

@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: str,
    current_user: User = Depends(get_current_user_dependency)
):
    """Delete project and associated files"""
    project = await Project.get(project_id)
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check ownership
    if project.user_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Delete files
    try:
        file_path = Path(project.file_path)
        if file_path.exists():
            file_path.unlink()
    except Exception as e:
        # Log error but don't fail the deletion
        print(f"Error deleting file: {e}")
    
    # Delete project record
    await project.delete()
    
    return {"message": "Project deleted successfully"}