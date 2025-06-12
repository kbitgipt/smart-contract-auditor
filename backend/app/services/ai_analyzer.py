import os
import json
import tempfile
from typing import Dict, List
from pathlib import Path
from openai import AsyncOpenAI

class AIAnalyzer:
    """Service for AI-powered vulnerability analysis using OpenAI"""
    
    def __init__(self):
        self.openai_client = AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            default_headers={"OpenAI-Beta": "assistants=v2"}
        )
        self.assistant_id = os.getenv("OPENAI_ASSISTANT_ID")  
        
        if not self.assistant_id:
            raise ValueError("OPENAI_ASSISTANT_ID must be set in environment variables")

    
    async def _read_file_safely(self, file_path: Path) -> str:
        """Safely read file with multiple encoding attempts"""
        try:
            encodings = ['utf-8', 'utf-8-sig', 'latin1', 'cp1252']
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        content = f.read()
                    return content
                except UnicodeDecodeError:
                    continue
            
            # If all encodings fail, read as binary and handle
            with open(file_path, 'rb') as f:
                binary_content = f.read()
                content = binary_content.decode('utf-8', errors='ignore')
                return content
                
        except Exception as e:
            print(f"❌ Error reading file {file_path}: {e}")
            return f"// ERROR: Could not read file {file_path.name}: {str(e)}"

# Handle upload source code on AI assistant    

    async def _upload_source_files(self, source_code: str, project_id: str, original_filename: str = None) -> str:
        """Upload source code file with .js extension and Solidity header"""
        try:
            # Check if source file already exists for this project
            existing_source_files = await self._find_existing_source_files(project_id)
            
            if original_filename:
                base_name = Path(original_filename).stem
                expected_filename = f"{project_id}_{base_name}.js"
            else:
                expected_filename = f"{project_id}_source.js"
            
            # Check if the exact file already exists
            for file_id in existing_source_files:
                try:
                    file_details = await self.openai_client.files.retrieve(file_id)
                    if file_details.filename == expected_filename:
                        print(f"✅ Reusing existing source file: {expected_filename}")
                        return file_id
                except Exception as e:
                    print(f"Error checking existing file {file_id}: {e}")
                    continue
            
            # If not found, upload new file
            print(f"📤 Uploading new source file: {expected_filename}")
            temp_dir = Path(tempfile.mkdtemp())
            source_file_path = temp_dir / expected_filename
            
            # Add header comment to indicate this is a Solidity file
            file_content = f"// SOLIDITY CONTRACT: {original_filename or 'source.sol'}\n"
            file_content += "// File extension changed to .js for OpenAI compatibility\n\n"
            file_content += source_code
            
            with open(source_file_path, 'w', encoding='utf-8') as f:
                f.write(file_content)
            
            # Upload to OpenAI
            with open(source_file_path, "rb") as f:
                file_obj = await self.openai_client.files.create(
                    file=f,
                    purpose="assistants"
                )
            
            # Clean up local temp file
            try:
                import shutil
                shutil.rmtree(temp_dir)
            except Exception as e:
                print(f"Error cleaning up temp directory: {e}")
            
            return file_obj.id
            
        except Exception as e:
            print(f"Error uploading source file: {e}")
            raise e

    async def _upload_foundry_source_files(self, main_contracts: List[str], project_id: str) -> List[str]:
        """Upload multiple source files for Foundry project with .js extension"""
        uploaded_file_ids = []
        try:
            # Get existing source files for this project
            existing_source_files = await self._find_existing_source_files(project_id)

            for contract_path in main_contracts:
                contract_path_obj = Path(contract_path)
                if contract_path_obj.exists():
                    original_filename = contract_path_obj.name
                    base_name = contract_path_obj.stem
                    expected_filename = f"{project_id}_{base_name}.js"
                    
                    # Check if file already exists
                    file_id_found = None
                    for file_id in existing_source_files:
                        try:
                            file_details = await self.openai_client.files.retrieve(file_id)
                            if file_details.filename == expected_filename:
                                print(f"✅ Reusing existing Foundry source file: {expected_filename}")
                                file_id_found = file_id
                                break
                        except Exception as e:
                            print(f"Error checking existing file {file_id}: {e}")
                            continue
                    
                    if file_id_found:
                        uploaded_file_ids.append(file_id_found)
                    else:
                        # Upload new file
                        print(f"📤 Uploading new Foundry source file: {expected_filename}")
                        contract_content = await self._read_file_safely(contract_path_obj)
                        
                        temp_dir = Path(tempfile.mkdtemp())
                        temp_file_path = temp_dir / expected_filename
                        
                        # Add header comment to indicate this is a Solidity file
                        file_content = f"// SOLIDITY CONTRACT: {original_filename}\n"
                        file_content += "// File extension changed to .js for OpenAI compatibility\n\n"
                        file_content += contract_content
                        
                        with open(temp_file_path, 'w', encoding='utf-8') as f:
                            f.write(file_content)
                        
                        with open(temp_file_path, "rb") as f:
                            file_obj = await self.openai_client.files.create(
                                file=f,
                                purpose="assistants"
                            )
                        
                    uploaded_file_ids.append(file_obj.id)

                    # Clean up local temp file
                    try:
                        import shutil
                        shutil.rmtree(temp_dir)
                    except Exception as e:
                        print(f"Error cleaning up temp directory: {e}")
            
            return uploaded_file_ids
            
        except Exception as e:
                    print(f"Error uploading Foundry source files: {e}")
                    # Clean up any uploaded files on error
                    await self._cleanup_assistant_files(uploaded_file_ids)
                    raise e
        
# Handle upload slither result on AI assistant 

    async def _upload_slither_results(self, slither_results: Dict, project_id: str) -> str:
        """Upload Slither analysis results as temporary file"""
        try:
            # Create temporary file for Slither results
            temp_dir = Path(tempfile.mkdtemp())
            slither_file_path = temp_dir / f"{project_id}_slither_analysis.json"
            
            with open(slither_file_path, 'w', encoding='utf-8') as f:
                json.dump(slither_results, f, indent=2)
            
            # Upload to OpenAI
            with open(slither_file_path, "rb") as f:
                file_obj = await self.openai_client.files.create(
                    file=f,
                    purpose="assistants"
                )
            
            # Clean up local temp file
            try:
                import shutil
                shutil.rmtree(temp_dir)
            except Exception as e:
                print(f"Error cleaning up temp directory: {e}")
            
            return file_obj.id
            
        except Exception as e:
            print(f"Error uploading Slither results: {e}")
            raise e

    async def _cleanup_assistant_files(self, file_ids: List[str]):
        """Delete files from OpenAI (v2 API doesn't need assistant file removal)"""
        for file_id in file_ids:
            try:
                # In v2, just delete the file directly
                await self.openai_client.files.delete(file_id)
                print(f"✅ Deleted file: {file_id}")
            except Exception as e:
                print(f"Error cleaning up file {file_id}: {e}")

    async def _find_existing_slither_files(self, project_id: str = None) -> List[str]:
        """Find existing Slither analysis files in assistant"""
        try:
            # Get all files attached to assistant
            files = await self.openai_client.files.list()
            
            slither_file_ids = []
            for file_info in files.data:
                # Get file details to check filename
                is_slither = "slither" in file_info.filename.lower()

                # If project_id is specified, also check if filename contains project_id
                if project_id:
                    is_project_match = project_id in file_info.filename
                    if is_slither and is_project_match:
                        slither_file_ids.append(file_info.id)
                else:
                    # If no project_id specified, return all slither files
                    if is_slither:
                        slither_file_ids.append(file_info.id)
            
            return slither_file_ids
            
        except Exception as e:
            print(f"Error finding existing Slither files: {e}")
            return []

    async def _find_existing_source_files(self, project_id: str) -> List[str]:
        """Find existing source files for a specific project"""
        try:
            files = await self.openai_client.files.list()
            
            source_file_ids = []
            for file_info in files.data:
                if file_info.filename:
                    # Check if filename contains project_id and is not a slither file
                    is_project_match = project_id in file_info.filename
                    is_not_slither = "slither" not in file_info.filename.lower()
                    
                    if is_project_match and is_not_slither:
                        source_file_ids.append(file_info.id)
            
            return source_file_ids
            
        except Exception as e:
            print(f"Error finding existing source files: {e}")
            return []

# Analyze single file with assistant - uploads source code + latest Slither results

    async def analyze_vulnerabilities(self, slither_results: Dict, source_code: str, project_id: str, original_filename: str = None) -> Dict:
        """Analyze single file with assistant - uploads source code + latest Slither results"""
        try:
            if not slither_results.get("success") or not slither_results.get("data"):
                return {
                    "success": False,
                    "error": "No valid Slither results to analyze"
                }
            
            detectors = slither_results["data"].get("results", {}).get("detectors", [])
            
            if not detectors:
                return {
                    "success": True,
                    "vulnerabilities": [],
                    "summary": {
                        "total": 0,
                        "high": 0,
                        "medium": 0,
                        "low": 0,
                        "informational": 0
                    },
                    "ai_recommendations": []
                }
            
            # Step 1: Clean up old Slither analysis files
            old_slither_files = await self._find_existing_slither_files(project_id)
            if old_slither_files:
                await self._cleanup_assistant_files(old_slither_files)
            
            # Step 2: Upload source code (keep in assistant)
            source_file_id = await self._upload_source_files(source_code, project_id, original_filename)
            
            # Step 3: Upload latest Slither results (temporary)
            slither_file_id = await self._upload_slither_results(slither_results, project_id)
            
            try:
                # Step 4: Create thread and run analysis
                thread = await self.openai_client.beta.threads.create()
                
                if original_filename:
                    base_name = Path(original_filename).stem
                    source_filename = f"{project_id}_{base_name}.js"
                else:
                    source_filename = f"{project_id}_source.js"
                slither_filename = f"{project_id}_slither_analysis.json"

                # Add message to thread
                await self.openai_client.beta.threads.messages.create(
                    thread_id=thread.id,
                    role="user",
                    content=f"""
Please analyze the smart contract security for:

**Contract File:** {original_filename or 'source.js'}
**Analysis Type:** Single File Analysis

I have uploaded:
1. The source code file: {source_filename}
2. The latest Slither static analysis results: {slither_filename}

Please provide a comprehensive security assessment by:

1. Reviewing the source code for business logic and security patterns
2. Validating each Slither finding against the actual source code
3. Identifying any additional vulnerabilities not caught by static analysis
4. Providing specific, actionable recommendations for each issue

Focus on practical security concerns that could impact the contract's operation or user funds.
""",
                    attachments=[
                        {"file_id": source_file_id, "tools": [{"type": "code_interpreter"}]},
                        {"file_id": slither_file_id, "tools": [{"type": "file_search"}]}
                    ]
                )
                
                # Run the assistant
                run = await self.openai_client.beta.threads.runs.create(
                    thread_id=thread.id,
                    assistant_id=self.assistant_id
                )
                
                # Wait for completion
                import asyncio
                while run.status in ["queued", "in_progress"]:
                    await asyncio.sleep(1)
                    run = await self.openai_client.beta.threads.runs.retrieve(
                        thread_id=thread.id,
                        run_id=run.id
                    )
                
                if run.status == "completed":
                    # Get the assistant's response
                    messages = await self.openai_client.beta.threads.messages.list(
                        thread_id=thread.id
                    )
                    
                    assistant_message = messages.data[0]
                    response_content = assistant_message.content[0].text.value
                    
                    # Parse JSON response
                    ai_analysis = json.loads(response_content)
                    
                    return {
                        "success": True,
                        "vulnerabilities": ai_analysis.get("vulnerabilities", []),
                        "summary": ai_analysis.get("summary", {}),
                        "ai_recommendations": ai_analysis.get("general_recommendations", [])
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Assistant run failed with status: {run.status}"
                    }
                
            finally:
                # Step 5: Clean up Slither file (keep source code)
                await self._cleanup_assistant_files([slither_file_id])
                
        except Exception as e:
            print(f"Assistant analysis error: {e}")
            return {
                "success": False,
                "error": f"AI analysis failed: {str(e)}"
            }

# Analyze foundry project with assistant 

    async def analyze_foundry_project(self, slither_results: Dict, main_contracts: List[str], project_id: str) -> Dict:
        """Analyze Foundry project using Assistant API with .js files"""
        try:
            # Step 1: Clean up old Slither files only (keep source files)
            old_slither_files = await self._find_existing_slither_files(project_id)
            if old_slither_files:
                print(f"🗑️ Cleaning up {len(old_slither_files)} old Slither files for project {project_id}")
                await self._cleanup_assistant_files(old_slither_files)
            
            # Step 2: Upload or reuse source files
            source_file_ids = await self._upload_foundry_source_files(main_contracts, project_id)
            
            # Step 3: Upload fresh Slither results
            temp_dir = Path(tempfile.mkdtemp())
            slither_file_path = temp_dir / f"{project_id}_slither_results.json"
            with open(slither_file_path, 'w', encoding='utf-8') as f:
                json.dump(slither_results, f, indent=2)
            
            with open(slither_file_path, "rb") as f:
                slither_file = await self.openai_client.files.create(
                    file=f,
                    purpose="assistants"
                )
            
            try:
                # Step 4: Create thread and run analysis using Assistant
                thread = await self.openai_client.beta.threads.create()
                
                # Create comprehensive analysis prompt
                contract_names = [Path(c).name for c in main_contracts]
                uploaded_filenames = [f"{project_id}_{Path(c).stem}.js" for c in main_contracts]
                
                prompt = f"""
Please analyze the smart contract security for this Foundry project:

**Project ID:** {project_id}
**Analysis Type:** Foundry Project Analysis

I have uploaded:
- Contract files: {', '.join(uploaded_filenames)} (Solidity code with .js extension for compatibility)
- Slither analysis results: {project_id}_slither_results.json

**Original contract files analyzed:** {', '.join(contract_names)}

Please provide a comprehensive security assessment by:

1. **Project Overview**: Analyze the project structure and identify main contracts and their relationships
2. **Vulnerability Analysis**: Review all Slither findings and validate them against the source code
3. **Cross-Contract Analysis**: Identify potential issues in contract interactions and dependencies
4. **Architecture Review**: Assess the overall security architecture and design patterns
5. **Foundry-Specific Issues**: Check for testing coverage, deployment scripts, and configuration issues

Note: All source files have .js extension for upload compatibility but contain Solidity smart contract code.
Focus on practical security concerns that could impact the contracts' operation or user funds.
"""
                
                # Prepare file attachments
                # all_file_ids = source_file_ids + [slither_file.id]
                attachments=[
                        {"file_id": source_file_ids, "tools": [{"type": "code_interpreter"}]},
                        {"file_id": slither_file.id, "tools": [{"type": "file_search"}]}
                    ]
                # for file_id in all_file_ids:
                #     attachments.append({
                #         "file_id": file_id, 
                #         "tools": [{"type": "code_interpreter"}]
                #     })
                
                # Add message to thread
                await self.openai_client.beta.threads.messages.create(
                    thread_id=thread.id,
                    role="user",
                    content=prompt,
                    attachments=attachments
                )
                
                # Run the assistant
                run = await self.openai_client.beta.threads.runs.create(
                    thread_id=thread.id,
                    assistant_id=self.assistant_id
                )
                
                # Wait for completion
                import asyncio
                while run.status in ["queued", "in_progress"]:
                    await asyncio.sleep(1)
                    run = await self.openai_client.beta.threads.runs.retrieve(
                        thread_id=thread.id,
                        run_id=run.id
                    )
                
                if run.status == "completed":
                    # Get the assistant's response
                    messages = await self.openai_client.beta.threads.messages.list(
                        thread_id=thread.id
                    )
                    
                    assistant_message = messages.data[0]
                    response_content = assistant_message.content[0].text.value
                    
                    # Try to parse as JSON, if not possible, create structured response
                    try:
                        ai_analysis = json.loads(response_content)
                    except json.JSONDecodeError:
                        # Create structured response from text
                        ai_analysis = {
                            "vulnerabilities": [],
                            "summary": {"total": 0, "high": 0, "medium": 0, "low": 0, "informational": 0},
                            "general_recommendations": [response_content],
                            "raw_analysis": response_content
                        }
                    
                    return {
                        "success": True,
                        "vulnerabilities": ai_analysis.get("vulnerabilities", []),
                        "summary": ai_analysis.get("summary", {}),
                        "ai_recommendations": ai_analysis.get("general_recommendations", []),
                        "project_analysis": True
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Assistant run failed with status: {run.status}"
                    }
                
            finally:
                # Step 5: Clean up only Slither file (keep source files for reuse)
                print(f"🗑️ Cleaning up temporary Slither file for project {project_id}")
                await self._cleanup_assistant_files([slither_file.id])
                
                # Clean up local temp directory
                try:
                    import shutil
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    print(f"Error cleaning up temp directory: {e}")
                    
        except Exception as e:
            print(f"Foundry project analysis error: {e}")
            return {
                "success": False,
                "error": f"Foundry analysis failed: {str(e)}"
            }

