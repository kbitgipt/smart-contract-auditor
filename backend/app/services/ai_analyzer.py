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
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Response schema for structured output
        self.vulnerability_schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "vulnerabilities": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "id": {"type": "string"},
                            "title": {"type": "string"},
                            "description": {"type": "string"},
                            "severity": {"type": "string", "enum": ["HIGH", "MEDIUM", "LOW", "INFORMATIONAL"]},
                            "impact": {"type": "string"},
                            "recommendation": {"type": "string"},
                            "code_snippet": {"type": "string"},
                            "references": {"type": "array", "items": {"type": "string"}}
                        },
                        "required": ["id", "title", "description", "severity", "impact", "recommendation", "code_snippet", "references"]
                    }
                },
                "summary": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "total": {"type": "integer"},
                        "high": {"type": "integer"},
                        "medium": {"type": "integer"},
                        "low": {"type": "integer"},
                        "informational": {"type": "integer"}
                    },
                    "required": ["total", "high", "medium", "low", "informational"]
                },
                "general_recommendations": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "required": ["vulnerabilities", "summary", "general_recommendations"]
        }
    
    async def _read_file_safely(self, file_path: Path) -> str:
        """Safely read file with multiple encoding attempts"""
        try:
            # Try multiple encodings
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

    async def analyze_vulnerabilities(self, slither_results: Dict, source_code: str) -> Dict:
        """Analyze Slither results with OpenAI using file uploads for better processing"""
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
            
            # Create temporary files for source code and Slither output
            source_file_id, slither_file_id = await self._upload_analysis_files(
                source_code, slither_results
            )
            
            try:
                # Create analysis prompt that references the uploaded files
                prompt = self._create_file_based_analysis_prompt()
                
                response = await self.openai_client.chat.completions.create(
                    model="gpt-4.1-nano",  # Use GPT-4 for better file processing
                    messages=[
                        {
                            "role": "user",
                            "content": prompt,
                            "attachments": [
                                {"file_id": source_file_id, "tools": [{"type": "code_interpreter"}]},
                                {"file_id": slither_file_id, "tools": [{"type": "file_search"}]}
                            ]
                        }
                    ],
                    response_format={
                        "type": "json_schema",
                        "json_schema": {
                            "name": "vulnerability_analysis",
                            "strict": True,
                            "schema": self.vulnerability_schema
                        }
                    },
                    temperature=0.1,
                    max_tokens=6000
                )
                
                # Parse OpenAI response
                ai_analysis = json.loads(response.choices[0].message.content)
                
                return {
                    "success": True,
                    "vulnerabilities": ai_analysis.get("vulnerabilities", []),
                    "summary": ai_analysis.get("summary", {}),
                    "ai_recommendations": ai_analysis.get("general_recommendations", [])
                }
                
            finally:
                # Clean up uploaded files
                await self._cleanup_files([source_file_id, slither_file_id])
                
        except Exception as e:
            print(f"OpenAI analysis error: {e}")
            return {
                "success": False,
                "error": f"AI analysis failed: {str(e)}"
            }
    
    async def _upload_analysis_files(self, source_code: str, slither_results: Dict) -> tuple:
        """Upload source code and Slither results as files to OpenAI"""
        
        # Create temporary directory
        temp_dir = Path(tempfile.mkdtemp())
        
        try:
            # Write source code to file
            source_file_path = temp_dir / "contract_source.js"
            with open(source_file_path, 'w', encoding='utf-8') as f:
                f.write("// SOLIDITY SMART CONTRACT CODE\n")
                f.write("// File extension changed to .js for OpenAI compatibility\n")
                f.write(source_code)
            
            # Write Slither results to JSON file
            slither_file_path = temp_dir / "slither_analysis.json"
            with open(slither_file_path, 'w', encoding='utf-8') as f:
                json.dump(slither_results, f, indent=2)
            
            # Upload files to OpenAI
            source_file = await self.openai_client.files.create(
                file=open(source_file_path, "rb"),
                purpose="assistants"
            )
            
            slither_file = await self.openai_client.files.create(
                file=open(slither_file_path, "rb"),
                purpose="assistants"
            )
            
            return source_file.id, slither_file.id
            
        except Exception as e:
            print(f"Error uploading files: {e}")
            raise e
        finally:
            # Clean up local temporary files
            try:
                import shutil
                shutil.rmtree(temp_dir)
            except Exception as e:
                print(f"Error cleaning up temp directory: {e}")
    
    def _create_file_based_analysis_prompt(self) -> str:
        """Create analysis prompt that references uploaded files"""
        
        prompt = """
I have uploaded two files for smart contract security analysis:

1. **contract_source.js** - The Solidity smart contract source code
2. **slither_analysis.json** - The raw output from Slither static analysis tool

Please analyze these files and provide a comprehensive security assessment following these requirements:

## Analysis Tasks:

1. **Review the source code** to understand the contract's functionality and business logic
2. **Examine the Slither findings** to identify specific vulnerabilities and issues
3. **Cross-reference** Slither findings with the actual source code for validation
4. **Categorize vulnerabilities** by severity using these guidelines:
   - **HIGH**: Direct loss of funds, unauthorized access, critical business logic flaws
   - **MEDIUM**: Potential loss of funds, access control issues, state manipulation
   - **LOW**: Best practice violations, minor logic issues, optimization opportunities
   - **INFORMATIONAL**: Code quality, documentation, style improvements

## Output Requirements:

For each vulnerability found:
- Generate a unique ID
- Provide clear title and description
- Assess severity level
- Explain potential impact
- Give specific remediation recommendations
- Include relevant code snippets where applicable
- Add references to additional resources if helpful

Also provide:
- Summary statistics of all findings
- General security recommendations for the contract

Use the code interpreter to analyze patterns in the source code and file search to examine the Slither output structure. Focus on providing actionable, specific recommendations that developers can implement immediately.
"""
        return prompt
    
    async def _cleanup_files(self, file_ids: List[str]):
        """Clean up uploaded files from OpenAI"""
        for file_id in file_ids:
            try:
                await self.openai_client.files.delete(file_id)
            except Exception as e:
                print(f"Error deleting file {file_id}: {e}")
    
    async def enhance_vulnerability_analysis(self, vulnerability: Dict, source_code: str) -> Dict:
        """Enhance individual vulnerability with more detailed AI analysis using file upload"""
        try:
            # Create temporary file for source code
            temp_dir = Path(tempfile.mkdtemp())
            source_file_path = temp_dir / "contract_source.sol"
            
            with open(source_file_path, 'w', encoding='utf-8') as f:
                f.write("// SOLIDITY SMART CONTRACT CODE\n")
                f.write("// File extension changed to .js for OpenAI compatibility\n\n")
                f.write(source_code)
            
            # Upload source file
            source_file = await self.openai_client.files.create(
                file=open(source_file_path, "rb"),
                purpose="assistants"
            )
            
            try:
                prompt = f"""
I have uploaded the smart contract source code and need detailed analysis of this specific vulnerability:

**VULNERABILITY:**
{json.dumps(vulnerability, indent=2)}

Please analyze the uploaded source code and provide:

1. **Detailed explanation** of how this vulnerability manifests in the code
2. **Step-by-step exploitation scenario** showing how an attacker could exploit this
3. **Specific code fix** with before/after examples from the actual source
4. **Prevention strategies** to avoid similar issues in the future
5. **Risk assessment** considering the contract's specific implementation

Use the code interpreter to analyze the source code and identify the exact locations and patterns related to this vulnerability.
"""
                
                response = await self.openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "user",
                            "content": prompt,
                            "attachments": [
                                {"file_id": source_file.id, "tools": [{"type": "code_interpreter"}]}
                            ]
                        }
                    ],
                    temperature=0.1,
                    max_tokens=2000
                )
                
                return {
                    "success": True,
                    "enhanced_analysis": response.choices[0].message.content
                }
                
            finally:
                # Clean up uploaded file
                await self._cleanup_files([source_file.id])
                
                # Clean up local temp file
                try:
                    import shutil
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    print(f"Error cleaning up temp directory: {e}")
                    
        except Exception as e:
            return {
                "success": False,
                "error": f"Enhancement failed: {str(e)}"
            }
    
    async def analyze_foundry_project(self, project_structure: Dict, slither_results: Dict, main_contracts: List[str]) -> Dict:
        """Analyze Foundry project with comprehensive file upload approach"""
        try:
            # Create temporary directory for project files
            temp_dir = Path(tempfile.mkdtemp())
            uploaded_files = []
            
            try:
                # Upload main contract files
                for i, contract_path in enumerate(main_contracts):
                    contract_path_obj = Path(contract_path)
                    if contract_path_obj.exists():
                        # Use safe file reading
                        contract_content = await self._read_file_safely(contract_path_obj)

                        # Read content and save as .js file
                        with open(contract_path, 'r', encoding='utf-8') as f:
                            contract_content = f.read()
                        
                        # Create .js file with Solidity content
                        js_file_path = temp_dir / f"contract_{i}.js"
                        with open(js_file_path, 'w', encoding='utf-8') as f:
                            f.write(f"// SOLIDITY CONTRACT: {Path(contract_path).name}\n")
                            f.write("// File extension changed to .js for OpenAI compatibility\n\n")
                            f.write(contract_content)
                        
                        with open(js_file_path, "rb") as f:
                            contract_file = await self.openai_client.files.create(
                                file=f,
                                purpose="assistants"
                            )
                        uploaded_files.append(contract_file.id)
                
                # Upload project structure as JSON
                structure_file_path = temp_dir / "project_structure.json"
                with open(structure_file_path, 'w', encoding='utf-8') as f:
                    json.dump(project_structure, f, indent=2)
                
                structure_file = await self.openai_client.files.create(
                    file=open(structure_file_path, "rb"),
                    purpose="assistants"
                )
                uploaded_files.append(structure_file.id)
                
                # Upload Slither results
                slither_file_path = temp_dir / "slither_results.json"
                with open(slither_file_path, 'w', encoding='utf-8') as f:
                    json.dump(slither_results, f, indent=2)
                
                slither_file = await self.openai_client.files.create(
                    file=open(slither_file_path, "rb"),
                    purpose="assistants"
                )
                uploaded_files.append(slither_file.id)
                
                # Create comprehensive analysis prompt
                uploaded_contract_count = len([f for f in uploaded_files if 'contract_' in str(f)])
                prompt = f"""
I have uploaded a Foundry project for comprehensive security analysis:

**Files uploaded:**
- {uploaded_contract_count} Solidity contract files (renamed to .js for compatibility)
- project_structure.json - Complete project structure and metadata
- slither_results.json - Static analysis results from Slither

**Contract files analyzed:** {', '.join([Path(c).name for c in main_contracts[:uploaded_contract_count]])}

Please provide a comprehensive security assessment of this Foundry project:

1. **Project Overview**: Analyze the project structure and identify the main contracts and their relationships
2. **Vulnerability Analysis**: Review all Slither findings and validate them against the source code
3. **Cross-Contract Analysis**: Identify potential issues in contract interactions and dependencies
4. **Architecture Review**: Assess the overall security architecture and design patterns
5. **Foundry-Specific Issues**: Check for testing coverage, deployment scripts, and configuration issues

Use both file search and code interpreter to thoroughly analyze all uploaded files and provide actionable security recommendations.
"""
                
                # Prepare file attachments
                attachments = []
                for file_id in uploaded_files:
                    attachments.append({
                        "file_id": file_id, 
                        "tools": [{"type": "code_interpreter"}, {"type": "file_search"}]
                    })
                
                response = await self.openai_client.chat.completions.create(
                    model="gpt-4.1-nano",  
                    messages=[
                        {
                            "role": "user",
                            "content": prompt,
                            "attachments": attachments
                        }
                    ],
                    response_format={
                        "type": "json_schema",
                        "json_schema": {
                            "name": "foundry_analysis",
                            "strict": True,
                            "schema": self.vulnerability_schema
                        }
                    },
                    temperature=0.1,
                    max_tokens=9000
                )
                
                # Parse response
                ai_analysis = json.loads(response.choices[0].message.content)
                
                return {
                    "success": True,
                    "vulnerabilities": ai_analysis.get("vulnerabilities", []),
                    "summary": ai_analysis.get("summary", {}),
                    "ai_recommendations": ai_analysis.get("general_recommendations", []),
                    "project_analysis": True
                }
                
            finally:
                # Clean up all uploaded files
                await self._cleanup_files(uploaded_files)
                
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
        
