import os, json, asyncio, re, shutil
from pathlib import Path
from pydantic import BaseModel
from typing import Dict, List, Optional

class SlitherOptions(BaseModel):
    """Slither analysis options for auditors"""
    target_files: Optional[List[str]] = None  # Specific files to analyze
    detectors: Optional[List[str]] = None     # Specific detectors to run
    exclude_detectors: Optional[List[str]] = None  # Detectors to exclude
    solc_version: Optional[str] = None        # Specific solc version
    exclude_dependencies: bool = True         # Exclude lib dependencies
    exclude_informational: bool = False       # Exclude informational findings
    exclude_optimization: bool = False        # Exclude optimization findings
    exclude_low: bool = False                # Exclude low severity findings

class StaticAnalyzer:
    """Service for static analysis using Slither"""
    def __init__(self):
        # Detect if running in Docker
        if os.path.exists('/.dockerenv'):
            self.slither_path = "slither"  # Use global slither in Docker
        else:
            self.slither_path = "/backend/venv/bin/slither" # your local slither path

    # Supported Slither detectors
    AVAILABLE_DETECTORS = [
        # Security Critical
        "reentrancy-eth", "reentrancy-no-eth", "reentrancy-unlimited-gas",
        "uninitialized-state", "uninitialized-storage", "uninitialized-local",
        "arbitrary-send", "controlled-delegatecall", "delegatecall-loop",
        "msg-value-loop", "tx-origin", 
        
        # Code Quality
        "assembly", "assert-state-change", "boolean-equal", 
        "deprecated-standards", "erc20-interface", "erc721-interface",
        "incorrect-equality", "locked-ether", "mapping-deletion",
        
        # Naming & Shadowing
        "shadowing-abstract", "shadowing-builtin", "shadowing-local", 
        "shadowing-state", "similar-names", "spelled-return-bool",
        
        # Logic Issues
        "timestamp", "tautology", "boolean-cst", "unused-return",
        "unused-state", "costly-loop", "dead-code",
        
        # Informational
        "reentrancy-benign", "reentrancy-events", "variable-scope",
        "low-level-calls", "naming-convention", "pragma", "solc-version",
        "external-function", "public-mappings-vars", "missing-zero-check",
        "calls-loop", "multiple-constructors", "too-many-digits"
    ]
    
    # Supported Solidity versions for single file analysis
    SUPPORTED_SOLC_VERSIONS = [
        "^0.8.0", "^0.8.20", "^0.8.21", "0.8.26"
    ]
    
    def get_available_detectors(self) -> List[str]:
        """Get list of available Slither detectors"""
        return self.AVAILABLE_DETECTORS
    
    def get_detector_categories(self) -> Dict[str, List[str]]:
        """Get detectors organized by category"""
        return {
            "security": [
                "reentrancy-eth", "reentrancy-no-eth", "reentrancy-unlimited-gas",
                "uninitialized-state", "uninitialized-storage", "uninitialized-local",
                "arbitrary-send", "controlled-delegatecall", "delegatecall-loop",
                "msg-value-loop", "tx-origin"
            ],
            "code_quality": [
                "assembly", "assert-state-change", "boolean-equal", 
                "deprecated-standards", "erc20-interface", "erc721-interface",
                "incorrect-equality", "locked-ether", "mapping-deletion"
            ],
            "naming": [
                "shadowing-abstract", "shadowing-builtin", "shadowing-local", 
                "shadowing-state", "similar-names", "spelled-return-bool"
            ],
            "optimization": [
                "timestamp", "tautology", "boolean-cst", "unused-return",
                "unused-state", "costly-loop", "dead-code"
            ],
            "informational": [
                "reentrancy-benign", "reentrancy-events", "variable-scope",
                "low-level-calls", "naming-convention", "pragma", "solc-version"
            ]
        }
    
    @staticmethod
    def detect_solidity_version(file_path: Path) -> Optional[str]:
        """Detect Solidity version from pragma statement"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find pragma solidity statements
            pragma_pattern = r'pragma\s+solidity\s+([^;]+);'
            matches = re.findall(pragma_pattern, content, re.IGNORECASE)
            
            if matches:
                return matches[0].strip()
            return None
        except Exception as e:
            print(f"Error detecting Solidity version: {e}")
            return None
    
    @classmethod
    def is_supported_solidity_version(cls, version: str) -> bool:
        """Check if Solidity version is supported for single file analysis"""
        if not version:
            return False
        
        # Clean version string
        clean_version = version.replace(' ', '').replace('>=', '^').replace('>', '^')
        
        # Check against supported versions
        for supported in cls.SUPPORTED_SOLC_VERSIONS:
            if clean_version.startswith(supported.replace('^', '')):
                return True
            if clean_version == supported:
                return True
        
        return False
    
# Static single file analysis methods
    
    async def run_slither_analysis(self, file_path: Path) -> Dict:
        """Run Slither static analysis on single file"""
        try:
            if not file_path.exists():
                return {"success": False, "error": f"File not found: {file_path}"}
            
            if not os.access(file_path, os.R_OK):
                return {"success": False, "error": f"Cannot read file: {file_path}"}
            
            absolute_file_path = file_path.resolve()

            cmd = [
                self.slither_path,
                str(absolute_file_path),
                '--json', '-',
                '--disable-color',
                '--solc-disable-warnings'
            ]

            env = os.environ.copy()
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                # cwd=str(file_path.parent)
            )
            
            stdout, stderr = await process.communicate()

            # Decode output
            stdout_str = stdout.decode('utf-8', errors='ignore') if stdout else ""
            stderr_str = stderr.decode('utf-8', errors='ignore') if stderr else ""
            
            print(f"Slither return code: {process.returncode}")

            if process.returncode not in [0, 1, 255] and not stdout_str.strip():
                return {
                    "success": False,
                    "error": f"Slither failed with code {process.returncode}",
                    "stderr": stderr_str
                }
            
            # QUAN TRỌNG: Slither return codes
            # 0: No issues found
            # 1: Issues found, but analysis successful
            # 255: Issues found (vulnerabilities detected)
            # Other codes: Real errors
            
            # Kiểm tra có JSON output không (quan trọng hơn return code)
            if stdout_str.strip():
                try:
                    # Thử parse JSON
                    slither_data = json.loads(stdout_str)

                    # Debug: print structure
                    if isinstance(slither_data, dict):
                        # print(f"🔑 JSON keys: {list(slither_data.keys())}")

                        # Check for detectors in different locations
                        # detectors_found = self._debug_detector_location(slither_data)
                        # print(f"🐛 Detectors found in structure: {detectors_found}")

                        return {
                            "success": True,
                            "data": slither_data,
                            "raw_output": stdout_str,
                            "return_code": process.returncode
                        }
                        
                except json.JSONDecodeError as e:
                    print(f"❌ JSON parsing failed: {e}")
                    return {
                        "success": False,
                        "error": f"Failed to parse Slither JSON output: {e}",
                        "raw_output": stdout_str,
                        "stderr": stderr_str
                    }
            else:
                # Không có output - check lỗi thực sự
                print("No stdout output from Slither")
                return {
                    "success": True,
                    "data": {
                        "success": True, 
                        "error": None, 
                        "results": {"detectors": []}
                        },
                    "raw_output": "No vulnerabilities found",
                    "return_code": process.returncode
                }
            
        except FileNotFoundError:
            return {
                "success": False,
                "error": "Slither command not found. Please ensure Slither is installed and in PATH"
            }
        except Exception as e:
            print(f"❌ Exception in run_slither_analysis: {e}")
            return {"success": False, "error": f"Failed to run Slither: {str(e)}"}

    '''def _debug_detector_location(self, data: Dict) -> Dict:
        """Debug helper to find where detectors are located in JSON"""
        locations = {}
        
        if isinstance(data, dict):
            # Check direct detectors
            if "detectors" in data:
                detectors = data["detectors"]
                locations["data.detectors"] = f"Found {len(detectors) if isinstance(detectors, list) else 0} detectors"
            
            # Check results.detectors
            if "results" in data and isinstance(data["results"], dict):
                results = data["results"]
                if "detectors" in results:
                    detectors = results["detectors"]
                    locations["data.results.detectors"] = f"Found {len(detectors) if isinstance(detectors, list) else 0} detectors"
                
                # Check other possible locations
                for key in results.keys():
                    if "detect" in key.lower() or "vuln" in key.lower():
                        locations[f"data.results.{key}"] = f"Found key: {key}"
            
            # Check all top-level keys for debugging
            for key in data.keys():
                if "detect" in key.lower() or "vuln" in key.lower() or "issue" in key.lower():
                    locations[f"data.{key}"] = f"Found key: {key}"
        
        return locations'''

# Run Slither analysis with custom options for auditors 

    async def run_slither_analysis_with_options(
        self, 
        project_path: Path, 
        options: Optional[SlitherOptions] = None
    ) -> Dict:
        """Run Slither analysis with custom options for auditors"""
        
        try:
            cmd = [self.slither_path]
            
            absolute_project_path = project_path.resolve()
            # Target files or directory
            if options.target_files:
                # Analyze specific files
                for file_path in options.target_files:
                    # If project_path is a file, target_files are relative to its parent
                    if project_path.is_file():
                        full_path = project_path.parent / file_path
                    else:
                        # If project_path is a directory, target_files are relative to it
                        full_path = project_path / file_path
                    
                    if full_path.exists():
                        cmd.append(str(full_path.resolve()))
            else:
                # Analyze entire project
                cmd.append(str(absolute_project_path))
            
            # JSON output
            cmd.extend(['--json', '-'])
            
            # Detector options
            if options.detectors:
                cmd.extend(['--detect', ','.join(options.detectors)])
            elif options.exclude_detectors:
                cmd.extend(['--exclude', ','.join(options.exclude_detectors)])
            
            # IMPORTANT: Only add exclude flags if explicitly set to True
            # Don't add --exclude-dependencies for single files
            if project_path.is_file():
                # For single files, don't exclude dependencies by default
                pass
            elif options.exclude_dependencies:
                cmd.append('--exclude-dependencies')
            
            if options.exclude_informational:
                cmd.append('--exclude-informational')
            
            if options.exclude_optimization:
                cmd.append('--exclude-optimization')
            
            if options.exclude_low:
                cmd.append('--exclude-low')
            
            if options.solc_version:
                cmd.extend(['--solc', options.solc_version])
            
            # Other options
            cmd.extend(['--disable-color', '--solc-disable-warnings'])
            
            print(f"Running Slither with options: {' '.join(cmd)}")
            print(f"📍 Working directory: {os.getcwd()}")  # Stay in backend/
            # print(f"📍 Target absolute path: {absolute_project_path}")
            
            # Execute command
            env = os.environ.copy()
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                # cwd=str(project_path.parent)
            )
            
            stdout, stderr = await process.communicate()
            
            # Process results same as before
            stdout_str = stdout.decode('utf-8', errors='ignore') if stdout else ""
            stderr_str = stderr.decode('utf-8', errors='ignore') if stderr else ""
            
            if stdout_str.strip():
                try:
                    slither_data = json.loads(stdout_str)
                    return {
                        "success": True,
                        "data": slither_data,
                        "raw_output": stdout_str,
                        "return_code": process.returncode,
                        "options_used": options.dict()
                    }
                except json.JSONDecodeError as e:
                    return {
                        "success": False,
                        "error": f"Failed to parse Slither JSON output: {e}",
                        "raw_output": stdout_str,
                        "stderr": stderr_str
                    }
            else:
                if process.returncode in [0, 1, 255]:
                    return {
                        "success": True,
                        "data": {
                            "success": True,
                            "error": None,
                            "results": {"detectors": []}
                        },
                        "raw_output": "No issues found",
                        "return_code": process.returncode,
                        "options_used": options.dict()
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Slither failed with code {process.returncode}",
                        "stdout": stdout_str,
                        "stderr": stderr_str
                    }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to run Slither: {str(e)}"
            }

# Parse Slither results into standardized format

    def parse_slither_results(self, slither_results: Dict) -> Dict:
        """Parse Slither results into standardized format"""
        try:
            # Early return for failed results
            if not slither_results.get("success"):
                print("❌ Slither results marked as failed")
                return self._empty_result()
            
            data = slither_results.get("data")
            if not data:
                print("❌ No data found in Slither results")
                return self._empty_result()
            
            # Try multiple extraction methods
            detectors = self._extract_detectors_comprehensive(data)
            # print(f"🐛 Extracted {len(detectors)} detectors total")

            if not detectors:
                # print("⚠️ No detectors found!")
                # print("🔍 Final check - let's see the raw data structure:")
                # import json
                # print(f"📄 Complete JSON structure:")
                # try:
                #     formatted_json = json.dumps(data, indent=2)[:2000]
                #     print(formatted_json)
                # except:
                #     print(f"Unable to format JSON: {str(data)[:1000]}")
                return self._empty_result()
            
            # Process detectors
            vulnerabilities = []
            summary = {"total": 0, "high": 0, "medium": 0, "low": 0, "informational": 0}
            
            for i, detector in enumerate(detectors):
                if not isinstance(detector, dict):
                    # print(f"⚠️ Detector {i} is not a dict: {type(detector)}")
                    continue

                # print(f"🔍 Processing detector {i}: {list(detector.keys())}")

                # Extract and validate basic info
                impact = self._safe_get_string(detector, "impact", "").lower()
                confidence = self._safe_get_string(detector,"confidence", "").lower()
                check = self._safe_get_string(detector, "check", "Unknown Issue")
                description = self._safe_get_string(detector, "description", "No description available")
                
                # print(f"  Impact: {impact}, Confidence: {confidence}, Check: {check}")
                
                # Map impact to severity
                severity = self._map_impact_to_severity(impact)
                summary[severity.lower()] += 1
                summary["total"] += 1
                
                # Generate meaningful code snippet
                elements = detector.get("elements", [])
                code_snippet = self._extract_code_snippet_improved(elements)
                
                vulnerabilities.append({
                    "id": f"slither_{i + 1}",
                    "title": str(check),
                    "description": str(description),
                    "severity": severity,
                    "impact": impact.title() if impact else "Unknown",
                    "confidence": confidence.title() if confidence else "Unknown",
                    "recommendation": f"Review and fix {check.lower()} issue. Check Slither documentation for specific remediation steps.",
                    "code_snippet": code_snippet,
                    "references": ["https://github.com/crytic/slither"],
                    "raw_detector": detector
                })
            
            return {
                "vulnerabilities": vulnerabilities,
                "summary": summary,
                "raw_findings": detectors
            }
            
        except Exception as e:
            print(f"❌ Error in parse_slither_results: {e}")
            import traceback
            traceback.print_exc()
            return self._empty_result()

    def _empty_result(self) -> Dict:
        """Return empty result structure"""
        return {
            "vulnerabilities": [],
            "summary": {"total": 0, "high": 0, "medium": 0, "low": 0, "informational": 0},
            "raw_findings": []
        }

    def _map_impact_to_severity(self, impact: str) -> str:
        """Map Slither impact levels to severity"""
        severity_map = {
            "high": "HIGH",
            "medium": "MEDIUM", 
            "low": "LOW",
            "optimization": "INFORMATIONAL",
            "informational": "INFORMATIONAL"
        }
        return severity_map.get(impact, "INFORMATIONAL")

    def _extract_detectors_comprehensive(self, data: Dict) -> List:
        """Comprehensive detector extraction from various JSON structures"""
        detectors = []
        
        if not isinstance(data, dict):
            return detectors
        
        # Method 1: Direct detectors
        if "detectors" in data:
            direct_detectors = data["detectors"]
            if isinstance(direct_detectors, list):
                detectors.extend(direct_detectors)
                # print(f"📍 Found {len(direct_detectors)} detectors in data.detectors")
        
        # Method 2: results.detectors
        if "results" in data and isinstance(data["results"], dict):
            results = data["results"]
            if "detectors" in results:
                results_detectors = results["detectors"]
                if isinstance(results_detectors, list):
                    detectors.extend(results_detectors)
                    # print(f"📍 Found {len(results_detectors)} detectors in data.results.detectors")
        
        # Method 3: Check for other possible locations
        for key, value in data.items():
            if key not in ["detectors", "results"] and isinstance(value, list):
                # Check if this looks like detector data
                if value and isinstance(value[0], dict) and any(k in value[0] for k in ["check", "impact", "confidence"]):
                    detectors.extend(value)
                    # print(f"📍 Found {len(value)} detectors in data.{key}")
        
        # Remove duplicates if any
        seen = set()
        unique_detectors = []
        for detector in detectors:
            detector_str = str(detector.get("check", "")) + str(detector.get("description", ""))
            if detector_str not in seen:
                seen.add(detector_str)
                unique_detectors.append(detector)
        
        return unique_detectors
   
    def _safe_get_string(self, data: Dict, key: str, default: str = "") -> str:
        """Safely get string value from dict"""
        value = data.get(key, default)
        return str(value) if value is not None else default

    def _extract_code_snippet_improved(self, elements: List) -> str:
        """Improved code snippet extraction"""
        if not elements or not isinstance(elements, list):
            return "No code snippet available"
        
        snippet_parts = []
        for element in elements[:3]:  # Limit to first 3 elements
            if isinstance(element, dict):
                element_type = element.get('type', 'Unknown')
                element_name = element.get('name', 'Unknown')
                
                # Try to get source mapping info
                if 'source_mapping' in element:
                    source_mapping = element['source_mapping']
                    if isinstance(source_mapping, dict):
                        lines = source_mapping.get('lines', [])
                        if lines:
                            snippet_parts.append(f"{element_type} '{element_name}' at line {lines[0] if isinstance(lines, list) else lines}")
                        else:
                            snippet_parts.append(f"{element_type}: {element_name}")
                    else:
                        snippet_parts.append(f"{element_type}: {element_name}")
                else:
                    snippet_parts.append(f"{element_type}: {element_name}")
        
        return "\n".join(snippet_parts) if snippet_parts else "No code snippet available"

# Foundry analysis methods

    async def run_foundry_analysis(
        self, 
        project_path: Path, 
        options: Optional[SlitherOptions] = None
    ) -> Dict:
        """Run Slither analysis specifically for Foundry projects"""
        
        try:
            cmd = [self.slither_path]
            
            # For Foundry projects, analyze the entire project directory
            cmd.append(str(project_path.resolve()))
            
            # JSON output
            cmd.extend(['--json', '-'])
            
            # Foundry-specific options
            if options:
                # Target specific files if specified
                if options.target_files:
                    # Instead of analyzing entire project, analyze specific files
                    cmd = [self.slither_path]
                    for target_file in options.target_files:
                        file_path = project_path / target_file
                        if file_path.exists():
                            cmd.append(str(file_path.resolve()))
                    cmd.extend(['--json', '-'])
                
                # Detector options
                if options.detectors:
                    cmd.extend(['--detect', ','.join(options.detectors)])
                elif options.exclude_detectors:
                    cmd.extend(['--exclude', ','.join(options.exclude_detectors)])
                
                # Exclude options
                if options.exclude_dependencies:
                    cmd.append('--exclude-dependencies')
                
                if options.exclude_informational:
                    cmd.append('--exclude-informational')
                
                if options.exclude_optimization:
                    cmd.append('--exclude-optimization')
                
                if options.exclude_low:
                    cmd.append('--exclude-low')
            else:
                # Default Foundry analysis - exclude libs and dependencies
                cmd.extend([
                    '--exclude-dependencies',
                    '--exclude-optimization'
                ])
            
            # Other standard options
            cmd.extend(['--disable-color', '--solc-disable-warnings'])
            
            # Try to detect and use forge if available
            forge_path = shutil.which('forge')
            if forge_path:
                # Use forge clean first to ensure clean build environment
                clean_cmd = ['forge', 'clean']
                try:
                    clean_process = await asyncio.create_subprocess_exec(
                        *clean_cmd,
                        cwd=str(project_path),
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    await clean_process.communicate()
                    print(f"Running forge clean: {' '.join(clean_cmd)}")
                    print(f"Forge clean completed with return code: {clean_process.returncode}")
                except Exception as e:
                    print(f"Forge clean failed: {e} (continuing anyway)")
                    
                # Use forge build first to ensure compilation
                build_cmd = ['forge', 'build']
                try:
                    build_process = await asyncio.create_subprocess_exec(
                        *build_cmd,
                        cwd=str(project_path),
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    await build_process.communicate()
                    print(f"Running forge build: {' '.join(build_cmd)}")
                    
                    print(f"Forge build completed with return code: {build_process.returncode}")
                except Exception as e:
                    print(f"Forge build failed: {e} (continuing with Slither anyway)")
            
            print(f"Running Foundry analysis: {' '.join(cmd)}")
            
            # Execute Slither
            env = os.environ.copy()
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                cwd=str(project_path)  # Important: run from project directory
            )
            
            stdout, stderr = await process.communicate()
            
            # Process results
            stdout_str = stdout.decode('utf-8', errors='ignore') if stdout else ""
            stderr_str = stderr.decode('utf-8', errors='ignore') if stderr else ""
            
            print(f"Foundry Slither return code: {process.returncode}")
            
            if stdout_str.strip():
                try:
                    slither_data = json.loads(stdout_str)
                    return {
                        "success": True,
                        "data": slither_data,
                        "raw_output": stdout_str,
                        "return_code": process.returncode,
                        "project_type": "foundry",
                        "options_used": options.dict() if options else {}
                    }
                
                except json.JSONDecodeError as e:
                    return {
                        "success": False,
                        "error": f"Failed to parse Foundry Slither JSON output: {e}",
                        "raw_output": stdout_str,
                        "stderr": stderr_str
                    }
            else:
                # No vulnerabilities found
                if process.returncode in [0, 1, 255]:
                    return {
                        "success": True,
                        "data": {
                            "success": True,
                            "error": None,
                            "results": {"detectors": []}
                        },
                        "raw_output": "No issues found in Foundry project",
                        "return_code": process.returncode,
                        "project_type": "foundry"
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Foundry Slither failed with code {process.returncode}",
                        "stdout": stdout_str,
                        "stderr": stderr_str
                    }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to run Foundry analysis: {str(e)}"
            }

