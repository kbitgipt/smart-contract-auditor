from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from typing import Optional
from app.models.user import User
from app.models.project import Project, ProjectType, ProjectStatus
from app.schemas.project import UploadResponse, ProjectResponse
from app.services.file_service import FileService
from app.api.auth import get_current_user_dependency

router = APIRouter(tags=["Upload"])

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
            file_hash=file_hash,
            analysis_path=str(analysis_path),
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
                analysis_path=project.analysis_path,
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

