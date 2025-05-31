import os
import hashlib
import zipfile
import aiofiles
from pathlib import Path
from typing import Tuple, List
from fastapi import HTTPException, UploadFile
from datetime import datetime
# import tempfile
import shutil

class FileService:
    
    ALLOWED_EXTENSIONS = {'.sol', '.zip'}
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    UPLOAD_DIR = Path("uploads")
    EXTRACTED_DIR = Path("extracted")
    
    def __init__(self):
        self.UPLOAD_DIR.mkdir(exist_ok=True)
        self.EXTRACTED_DIR.mkdir(exist_ok=True)
    
    @staticmethod
    def validate_file(file: UploadFile) -> None:
        """Validate uploaded file"""
        if not file.filename:
            raise HTTPException(
                status_code=400,
                detail="No filename provided"
            )
            
        # Check file extension
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in FileService.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"File type not allowed. Only {', '.join(FileService.ALLOWED_EXTENSIONS)} are supported"
            )
        
        # Check file size (this is approximate, actual size checked during upload)
        if hasattr(file, 'size') and file.size > FileService.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size is {FileService.MAX_FILE_SIZE // (1024*1024)}MB"
            )
    
    @staticmethod
    def calculate_file_hash(file_path: Path) -> str:
        """Calculate SHA256 hash of file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    
    @staticmethod
    async def save_upload_file(file: UploadFile, user_id: str) -> Tuple[Path, int, str]:
        """Save uploaded file and return path, size, hash"""
        # Create user directory
        user_dir = FileService.UPLOAD_DIR / user_id
        user_dir.mkdir(exist_ok=True)
        
        # Generate unique filename
        timestamp = int(datetime.utcnow().timestamp())
        file_ext = Path(file.filename).suffix
        safe_filename = f"{timestamp}_{file.filename}"
        file_path = user_dir / safe_filename
        
        # Save file with size validation
        total_size = 0
        async with aiofiles.open(file_path, 'wb') as f:
            while chunk := await file.read(8192):  # Read in 8KB chunks
                total_size += len(chunk)
                if total_size > FileService.MAX_FILE_SIZE:
                    # Remove partial file
                    await f.close()
                    file_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=400,
                        detail=f"File too large. Maximum size is {FileService.MAX_FILE_SIZE // (1024*1024)}MB"
                    )
                await f.write(chunk)
        
        # Calculate hash
        file_hash = FileService.calculate_file_hash(file_path)
        
        return file_path, total_size, file_hash
    
    @staticmethod
    def is_safe_path(path: str, base_path: str) -> bool:
        """Check if extracted path is safe (prevent directory traversal)"""
        abs_base = os.path.abspath(base_path)
        abs_path = os.path.abspath(os.path.join(base_path, path))
        return abs_path.startswith(abs_base)
    
    @staticmethod
    def extract_zip_safely(zip_path: Path, extract_to: Path) -> List[str]:
        """Safely extract ZIP file and return list of extracted files"""
        extracted_files = []
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            for member in zip_ref.namelist():
                # Security check: prevent directory traversal
                if not FileService.is_safe_path(member, str(extract_to)):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Unsafe file path in ZIP: {member}"
                    )
                
                # Extract file
                zip_ref.extract(member, extract_to)
                extracted_files.append(member)
                
                # Additional security: check file size after extraction
                extracted_file_path = extract_to / member
                if extracted_file_path.exists() and extracted_file_path.stat().st_size > FileService.MAX_FILE_SIZE:
                    # Remove large file
                    extracted_file_path.unlink()
                    raise HTTPException(
                        status_code=400,
                        detail=f"Extracted file too large: {member}"
                    )
        
        return extracted_files
    
    @staticmethod
    def detect_project_type(file_path: Path) -> Tuple[str, Path]:
        """Detect project type and return type and analysis path"""
        if file_path.suffix.lower() == '.sol':
            return "single_file", file_path
        
        elif file_path.suffix.lower() == '.zip':
            # Extract to temporary directory
            extract_dir = FileService.EXTRACTED_DIR / f"temp_{int(datetime.utcnow().timestamp())}"
            extract_dir.mkdir(exist_ok=True)
            
            try:
                extracted_files = FileService.extract_zip_safely(file_path, extract_dir)
                
                # Check if it's a Foundry project
                if FileService.is_foundry_project(extract_dir):
                    return "foundry_project", extract_dir
                else:
                    # Look for .sol files
                    sol_files = list(extract_dir.rglob("*.sol"))
                    if sol_files:
                        return "mixed_project", extract_dir
                    else:
                        raise HTTPException(
                            status_code=400,
                            detail="No Solidity files found in ZIP"
                        )
                        
            except Exception as e:
                # Cleanup on error
                if extract_dir.exists():
                    shutil.rmtree(extract_dir)
                raise e
        
        else:
            raise HTTPException(
                status_code=400,
                detail="Unsupported file type"
            )
    
    @staticmethod
    def is_foundry_project(project_path: Path) -> bool:
        """Check if directory is a Foundry project"""
        foundry_files = ['foundry.toml', 'forge.toml']
        return any((project_path / f).exists() for f in foundry_files)