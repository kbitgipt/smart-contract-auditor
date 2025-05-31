import os
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Optional
import re

class StaticAnalyzer:
    """Service for static analysis using Slither"""
    
    # Supported Solidity versions for single file analysis
    SUPPORTED_SOLC_VERSIONS = [
        "^0.8.0", "^0.8.21", "^0.8.22", "^0.8.23", "0.8.24", "0.8.25", "0.8.26"
    ]
    
    def __init__(self):
        self.slither_path = "slither"
    
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
    
    async def run_slither_analysis(self, file_path: Path) -> Dict:
        """Run Slither static analysis on single file"""
        try:
            # Kiểm tra file có tồn tại không
            if not file_path.exists():
                return {
                    "success": False,
                    "error": f"File not found: {file_path}"
                }
            
            # Kiểm tra quyền đọc file
            if not os.access(file_path, os.R_OK):
                return {
                    "success": False,
                    "error": f"Cannot read file: {file_path}"
                }
            
            cmd = [
                self.slither_path,
                str(file_path),
                '--json', '-',
                '--disable-color',
                '--solc-disable-warnings'
            ]
            
            print(f"Running Slither: {' '.join(cmd)}")
            print(f"File path: {file_path}")
            print(f"File exists: {file_path.exists()}")
            print(f"Working directory: {os.getcwd()}")
            
            # Thiết lập environment variables
            env = os.environ.copy()
            env['PATH'] = os.environ.get('PATH', '')
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                cwd=str(file_path.parent)
            )
            
            stdout, stderr = await process.communicate()
            
            print(f"Slither return code: {process.returncode}")
            print(f"Slither stdout: {stdout.decode('utf-8')[:500]}")
            print(f"Slither stderr: {stderr.decode('utf-8')[:500]}")
            
            # QUAN TRỌNG: Slither return codes
            # 0: No issues found
            # 1: Issues found, but analysis successful
            # 255: Issues found (vulnerabilities detected)
            # Other codes: Real errors
            
            # Kiểm tra có JSON output không (quan trọng hơn return code)
            stdout_str = stdout.decode('utf-8')
            stderr_str = stderr.decode('utf-8')
            
            # Nếu có JSON output, coi như thành công
            if stdout_str.strip():
                try:
                    # Thử parse JSON
                    slither_data = json.loads(stdout_str)
                    
                    # Kiểm tra structure cơ bản
                    if isinstance(slither_data, dict):
                        return {
                            "success": True,
                            "data": slither_data,
                            "raw_output": stdout_str,
                            "return_code": process.returncode
                        }
                    else:
                        return {
                            "success": False,
                            "error": "Invalid JSON structure from Slither",
                            "raw_output": stdout_str,
                            "stderr": stderr_str
                        }
                        
                except json.JSONDecodeError as e:
                    return {
                        "success": False,
                        "error": f"Failed to parse Slither JSON output: {e}",
                        "raw_output": stdout_str,
                        "stderr": stderr_str
                    }
            else:
                # Không có output - check lỗi thực sự
                if process.returncode in [0, 1, 255]:
                    # Các return code này OK nhưng không có output
                    return {
                        "success": True,
                        "data": {"success": True, "error": None, "results": {"detectors": []}},
                        "raw_output": "No issues found",
                        "return_code": process.returncode
                    }
                else:
                    # Lỗi thực sự
                    return {
                        "success": False,
                        "error": f"Slither failed with code {process.returncode}",
                        "stdout": stdout_str,
                        "stderr": stderr_str
                    }
            
        except FileNotFoundError:
            return {
                "success": False,
                "error": "Slither command not found. Please ensure Slither is installed and in PATH"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to run Slither: {str(e)}"
            }
    
    def parse_slither_results(self, slither_results: Dict) -> Dict:
        """Parse Slither results into standardized format"""
        if not slither_results.get("success") or not slither_results.get("data"):
            return {
                "vulnerabilities": [],
                "summary": {"total": 0, "high": 0, "medium": 0, "low": 0, "informational": 0},
                "raw_findings": []
            }
        
        detectors = slither_results["data"].get("results", {}).get("detectors", [])
        
        vulnerabilities = []
        summary = {"total": 0, "high": 0, "medium": 0, "low": 0, "informational": 0}
        
        for detector in detectors:
            impact = detector.get("impact", "").lower()
            confidence = detector.get("confidence", "").lower()
            
            # Map Slither impact to severity
            if impact in ["high"]:
                severity = "HIGH"
                summary["high"] += 1
            elif impact in ["medium"]:
                severity = "MEDIUM"
                summary["medium"] += 1
            elif impact in ["low"]:
                severity = "LOW"
                summary["low"] += 1
            else:
                severity = "INFORMATIONAL"
                summary["informational"] += 1
            
            summary["total"] += 1
            
            vulnerabilities.append({
                "id": f"slither_{len(vulnerabilities) + 1}",
                "title": detector.get("check", "Unknown Issue"),
                "description": detector.get("description", "No description available"),
                "severity": severity,
                "impact": detector.get("impact", "Unknown"),
                "confidence": confidence,
                "recommendation": "Review Slither documentation for specific remediation steps",
                "code_snippet": str(detector.get("elements", [])),
                "references": ["https://github.com/crytic/slither"],
                "raw_detector": detector
            })
        
        return {
            "vulnerabilities": vulnerabilities,
            "summary": summary,
            "raw_findings": detectors
        }