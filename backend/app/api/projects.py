from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from app.models.user import User
from app.models.project import Project, ProjectStatus, ProjectType
from app.schemas.project import ProjectResponse, ProjectDetailResponse, ProjectSourceResponse
from app.api.auth import get_current_user_dependency
from pathlib import Path
from datetime import datetime

router = APIRouter(tags=["Projects"])

@router.get("/", response_model=List[ProjectResponse])
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

@router.get("/{project_id}", response_model=ProjectDetailResponse)
async def get_project_detail(
    project_id: str,
    current_user: User = Depends(get_current_user_dependency)
):
    """Get detailed project information"""
    project = await Project.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if project.user_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    return ProjectDetailResponse(
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
        updated_at=project.updated_at,
        file_path=project.file_path
    )

@router.get("/{project_id}/source", response_model=ProjectSourceResponse)
async def get_project_source(
    project_id: str,
    file_path: Optional[str] = None,
    current_user: User = Depends(get_current_user_dependency)
):
    """Get source code for project or specific file"""
    project = await Project.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if project.user_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        if project.project_type == ProjectType.SINGLE_FILE:
            # Single file project
            with open(project.file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
            return ProjectSourceResponse(
                project_id=project_id,
                file_path=project.original_filename,
                source_code=source_code,
                project_type=project.project_type
            )
            # return {
            #         "project_id": project_id,
            #         "file_path": project.original_filename,
            #         "source_code": source_code,
            #         "project_type": project.project_type
            #     }
        else:
            # Foundry project
            base_path = Path(project.file_path)
            if file_path:
                # Get specific file
                target_path = base_path / file_path
                if not target_path.exists() or not target_path.is_file():
                    raise HTTPException(status_code=404, detail="File not found")
                
                with open(target_path, 'r', encoding='utf-8') as f:
                    source_code = f.read()
                return ProjectSourceResponse(
                    project_id=project_id,
                    file_path=file_path,
                    source_code=source_code,
                    project_type=project.project_type
                )
            else:
                # Get file tree
                files = []
                for sol_file in base_path.rglob("*.sol"):
                    if sol_file.is_file():
                        rel_path = sol_file.relative_to(base_path)
                        files.append(str(rel_path))
                
                return ProjectSourceResponse(
                    project_id=project_id,
                    file_path=None,
                    source_code=None,
                    project_type=project.project_type,
                    available_files=files
                )
                # return {
                #         "project_id": project_id,
                #         "file_path": None,
                #         "source_code": None,
                #         "project_type": project.project_type,
                #         "available_files": files
                #     }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading source: {str(e)}")
    
@router.delete("/{project_id}")
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
            if file_path.is_file():
                file_path.unlink()
            elif file_path.is_dir():
                import shutil
                shutil.rmtree(file_path)
    except Exception as e:
        # Log error but don't fail the deletion
        print(f"Error deleting file: {e}")
    
    # Delete project record
    await project.delete()
    
    return {"message": "Project deleted successfully"}

@router.put("/{project_id}")
async def update_project(
    project_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    current_user: User = Depends(get_current_user_dependency)
):
    """Update project information"""
    project = await Project.get(project_id)
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check ownership
    if project.user_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Update fields
    if name is not None:
        project.name = name
    if description is not None:
        project.description = description
    
    project.updated_at = datetime.now(datetime.timezone.utc)()
    await project.save()
    
    return ProjectDetailResponse(
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
        updated_at=project.updated_at,
        file_path=project.file_path
    )