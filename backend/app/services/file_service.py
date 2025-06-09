import os, hashlib, zipfile, aiofiles, shutil
from pathlib import Path
from typing import Tuple, List, Dict, Optional
from fastapi import HTTPException, UploadFile
from datetime import datetime
from app.services.static_analyzer import SlitherOptions

class FileService:
    
    ALLOWED_EXTENSIONS = {'.sol', '.zip'}
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
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
                
                foundry_project_path = FileService._find_foundry_project_in_extracted(extract_dir)
                
                if foundry_project_path:
                    return "foundry_project", foundry_project_path
                else:
                    print("❌ No valid Foundry project found in ZIP")
                    # Clean up extracted directory if no valid project found
                    import shutil
                    shutil.rmtree(extract_dir, ignore_errors=True)
                    raise Exception("ZIP file does not contain a valid Foundry project")
                    
            except Exception as e:
                print(f"❌ Error processing ZIP file: {e}")
                raise Exception(f"Failed to process ZIP file: {str(e)}")
        
        else:
            print(f"❓ Unknown file type: {file_path.suffix}")
            raise Exception(f"Unsupported file type: {file_path.suffix}")
        
    @staticmethod
    def _find_foundry_project_in_extracted(extracted_path: Path) -> Optional[Path]:
        """
        Find actual Foundry project directory within extracted content.
        Returns the deepest directory that contains Foundry project structure.
        """
        # STRATEGY 1: Check if extracted directory itself is a Foundry project
        if FileService.is_foundry_project(extracted_path):
            return extracted_path
        
        # STRATEGY 2: Search in immediate subdirectories (most common case)
        immediate_subdirs = [d for d in extracted_path.iterdir() if d.is_dir()]
        
        for subdir in immediate_subdirs:
            print(f"   - Checking: {subdir.name}")
            if FileService.is_foundry_project(subdir):
                return subdir
        print("❌ No valid Foundry project found in extracted content")
        return None
        # STRATEGY 3: Deep search (recursive) for nested project structures
        # print("🔍 Performing deep search for Foundry project...")
        
        # foundry_candidates = []
        
        # def find_foundry_recursive(current_path: Path, depth: int = 0):
        #     """Recursively find Foundry projects, limiting depth to avoid infinite loops"""
            
        #     if depth > 3:  # Limit depth to avoid performance issues
        #         return
            
        #     try:
        #         for item in current_path.iterdir():
        #             if item.is_dir():
        #                 # Skip common non-project directories
        #                 skip_dirs = {'.git', 'node_modules', '__pycache__', '.vscode', 'target', 'out', 'cache'}
        #                 if item.name in skip_dirs:
        #                     continue
                        
        #                 # Check if this directory is a Foundry project
        #                 if FileService.is_foundry_project(item):
        #                     foundry_candidates.append(item)
        #                     print(f"🎯 Found Foundry candidate: {item}")
        #                 else:
        #                     # Recurse into subdirectory
        #                     find_foundry_recursive(item, depth + 1)
        #     except (PermissionError, OSError) as e:
        #         print(f"⚠️ Cannot access directory {current_path}: {e}")
        
        # # Start recursive search
        # find_foundry_recursive(extracted_path)
        
        # # STRATEGY 4: Select best candidate
        # if foundry_candidates:
        #     # Prefer the deepest/most specific project path
        #     # or the one with the most source files
        #     best_candidate = None
        #     best_score = 0
            
        #     for candidate in foundry_candidates:
        #         score = 0
                
        #         # Score based on project structure completeness
        #         if (candidate / 'foundry.toml').exists():
        #             score += 10
        #         if (candidate / 'src').exists():
        #             score += 5
        #             # Count .sol files in src
        #             src_files = len(list((candidate / 'src').rglob('*.sol')))
        #             score += src_files
        #         if (candidate / 'test').exists():
        #             score += 3
        #         if (candidate / 'lib').exists():
        #             score += 2
                
        #         print(f"📊 Candidate {candidate.name} score: {score}")
                
        #         if score > best_score:
        #             best_score = score
        #             best_candidate = candidate
            
        #     if best_candidate:
        #         print(f"🏆 Selected best Foundry project: {best_candidate}")
        #         return best_candidate
        
        # print("❌ No valid Foundry project found in extracted content")
        # return None
    
    @staticmethod
    def is_foundry_project(path: Path) -> bool:
        """Check if directory is a Foundry project with safe file reading"""

        if not path.exists() or not path.is_dir():
            return False
        
        # Check for foundry.toml or foundry.json
        foundry_configs = ['foundry.toml', 'foundry.json']
        has_config = any((path / config).exists() for config in foundry_configs)
        
        if has_config:
            return True
        
        # Check for src/ or contracts/ directory with .sol files
        source_dirs = ['src', 'contracts']
        for source_dir in source_dirs:
            dir_path = path / source_dir
            if dir_path.exists() and any(dir_path.glob('*.sol')):
                return True
        # Additional check: lib/ directory with common Foundry deps
        lib_dir = path / 'lib'
        if lib_dir.exists():
            common_deps = ['forge-std', 'openzeppelin-contracts']
            has_foundry_deps = any((lib_dir / dep).exists() for dep in common_deps)
            if has_foundry_deps:
                return True
            
        return False

    @staticmethod
    def analyze_foundry_project_structure(project_path: Path) -> Dict:
        """Analyze Foundry project structure with error handling"""
        try:
            structure = {
                "source_files": [],
                "test_files": [],
                "script_files": [],
                "config_files": [],
            }
            
            # Find source files safely
            source_dirs = ['src', 'contracts']
            for source_dir in source_dirs:
                dir_path = project_path / source_dir
                if dir_path.exists() and dir_path.is_dir():
                    try:
                        for sol_file in dir_path.rglob('*.sol'):
                            try:
                                relative_path = str(sol_file.relative_to(project_path))
                                
                                if 'test' in relative_path.lower() or 'Test' in sol_file.name:
                                    structure["test_files"].append(relative_path)
                                else:
                                    structure["source_files"].append(relative_path)
                                    
                            except Exception as e:
                                print(f"⚠️ Error processing file {sol_file}: {e}")
                                continue
                                
                    except Exception as e:
                        print(f"⚠️ Error scanning directory {dir_path}: {e}")
                        continue
            
            # Find other files safely
            try:
                # Test files
                test_dir = project_path / 'test'
                if test_dir.exists():
                    for test_file in test_dir.rglob('*.sol'):
                        try:
                            relative_path = str(test_file.relative_to(project_path))
                            structure["test_files"].append(relative_path)
                        except Exception:
                            continue
                
                # Script files
                script_dir = project_path / 'script'
                if script_dir.exists():
                    for script_file in script_dir.rglob('*.sol'):
                        try:
                            relative_path = str(script_file.relative_to(project_path))
                            structure["script_files"].append(relative_path)
                        except Exception:
                            continue
                
                # Config files
                config_files = ['foundry.toml', 'forge.toml', 'remappings.txt']
                for config_file in config_files:
                    if (project_path / config_file).exists():
                        structure["config_files"].append(config_file)
                        
            except Exception as e:
                print(f"⚠️ Error scanning additional directories: {e}")
            
            return structure
            
        except Exception as e:
            print(f"❌ Error analyzing Foundry project structure: {e}")
            return {
                "source_files": [],
                "test_files": [],
                "script_files": [],
                "config_files": [],
                "error": str(e)
            }
    
    @staticmethod
    def get_foundry_analysis_options(project_path: Path) -> 'SlitherOptions':
        """Get recommended Slither options for Foundry project"""
        
        structure = FileService.analyze_foundry_project_structure(project_path)

        # Get main source files (exclude tests and dependencies)
        main_contracts = structure.get("source_files", [])

        options = SlitherOptions(
            target_files=main_contracts if main_contracts else None,
            detectors = [],
            exclude_dependencies=False,
            exclude_informational=False,  # Include for learning
            exclude_optimization=True,    # Skip gas optimizations
            exclude_low=False            # Include low severity
        )
        
        return options
    