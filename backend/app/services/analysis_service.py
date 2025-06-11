from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
from app.models.analysis import Analysis, AnalysisStatus, AnalysisType
from app.models.project import Project, ProjectType, ProjectStatus
from app.services.static_analyzer import StaticAnalyzer, SlitherOptions
from app.services.ai_analyzer import AIAnalyzer
from app.services.report_generator import ReportGenerator

class AnalysisService:
    """Main orchestrator for smart contract analysis"""
    
    def __init__(self):
        self.static_analyzer = StaticAnalyzer()
        self.ai_analyzer = AIAnalyzer()
        self.report_generator = ReportGenerator()
        
# Auto analysis
    async def perform_full_analysis(self, project: Project) -> Analysis:
        """Complete analysis workflow for normal users"""
        
        # Step 1: Static Analysis
        if project.project_type == ProjectType.FOUNDRY_PROJECT:
            analysis = await self.perform_foundry_static_analysis(project)
        else:
            analysis = await self._perform_single_file_static_analysis(project)

        # Step 2: AI Enhancement (for normal users)
        try:
            analysis = await self.perform_ai_enhancement(analysis)
        except Exception as e:
            print(f"AI enhancement failed, continuing with static results: {e}")
        
        # Step 3: Generate HTML report
        try:
            report_path = await self.generate_analysis_report(analysis, "html")
            analysis.report_path = report_path
            await analysis.save()
        except Exception as e:
            print(f"Report generation failed: {e}")
        
        return analysis

    async def analyze_single_vulnerability(self, vulnerability: Dict, source_code: str) -> Dict:
        """Analyze a single vulnerability in detail using AI"""
        return await self.ai_analyzer.enhance_vulnerability_analysis(vulnerability, source_code)
    
    def get_supported_versions(self) -> list:
        """Get list of supported Solidity versions"""
        return self.static_analyzer.SUPPORTED_SOLC_VERSIONS
    
    async def regenerate_report(self, analysis: Analysis, format_type: str = "html") -> str:
        """Regenerate report in specified format"""
        if not analysis.ai_analysis:
            raise Exception("No analysis data available for report generation")
        
        project = await Project.get(analysis.project_id)
        if not project:
            raise Exception("Project not found")
        
        if format_type == "html":
            return await self.report_generator.generate_html_report(analysis.ai_analysis, project)
        elif format_type == "json":
            return await self.report_generator.generate_json_report(analysis.ai_analysis, project)
        elif format_type == "markdown":
            return await self.report_generator.generate_markdown_report(analysis.ai_analysis, project)
        else:
            raise Exception(f"Unsupported format: {format_type}")

# Static analysis handle

    async def perform_foundry_static_analysis(
        self, 
        project: Project, 
        slither_options: Optional[SlitherOptions] = None
    ) -> Analysis:
        """Perform static analysis specifically for Foundry projects"""
        
        # Create analysis record
        analysis = Analysis(
            project_id=str(project.id),
            user_id=project.user_id,
            analysis_type=AnalysisType.SLITHER,
            status=AnalysisStatus.RUNNING,
            started_at=datetime.now(datetime.timezone.utc)()
        )
        await analysis.insert()
        
        try:
            # Update project status
            project.status = ProjectStatus.PROCESSING
            project.analysis_id = str(analysis.id)
            await project.save()
            
            project_path = Path(project.analysis_path)

            if not project_path.exists():
                raise Exception(f"Foundry project path not found: {project.analysis_path}")
            
            print(f"🔄 Starting Foundry static analysis for: {project_path}")
            
            # Analyze project structure
            from app.services.file_service import FileService
            project_structure = FileService.analyze_foundry_project_structure(project_path)
            
            print(f"📁 Foundry project structure:")
            print(f"  - Source files: {len(project_structure['source_files'])}")
            
            # Use custom options or generate recommended ones
            # if not slither_options:
            #     slither_options = FileService.get_foundry_analysis_options(project_path)
            #     print(f"📋 Using default Foundry options: {slither_options}")
            
            # Run Foundry-specific analysis
            slither_results = await self.static_analyzer.run_foundry_analysis(
                project_path, slither_options
            )
            
            print(f"📊 Foundry Slither analysis result: success={slither_results.get('success')}")
            
            if not slither_results.get("success"):
                error_msg = slither_results.get("error", "Unknown Foundry Slither error")
                stderr = slither_results.get("stderr", "")
                
                detailed_error = f"Foundry Slither analysis failed: {error_msg}"
                if stderr:
                    detailed_error += f"\nStderr: {stderr}"
                
                print(f"❌ {detailed_error}")
                
                # Update analysis with error
                analysis.status = AnalysisStatus.FAILED
                analysis.error_message = detailed_error
                analysis.completed_at = datetime.now(datetime.timezone.utc)()
                await analysis.save()
                
                # Update project status
                project.status = ProjectStatus.FAILED
                await project.save()
                
                raise Exception(detailed_error)
            
            # Parse static analysis results
            try:
                parsed_results = self.static_analyzer.parse_slither_results(slither_results)
                
                # Add Foundry-specific metadata
                parsed_results["foundry_metadata"] = {
                    "project_structure": project_structure,
                    "analysis_scope": {
                        "target_files": slither_options.target_files if slither_options else [],
                        "total_source_files": len(project_structure["source_files"]),
                        "analyzed_files": len(slither_options.target_files) if slither_options and slither_options.target_files else len(project_structure["source_files"])
                    }
                }
                
                summary = parsed_results.get('summary', {})
                print(f"📊 Foundry vulnerability summary: {summary}")
            
            except Exception as e:
                print(f"Error parsing Foundry Slither results: {e}")
                import traceback
                traceback.print_exc()
                # Create empty results but don't fail completely
                parsed_results = {
                    "vulnerabilities": [],
                    "summary": {"total": 0, "high": 0, "medium": 0, "low": 0, "informational": 0},
                    "raw_findings": [],
                    "parsing_error": str(e),
                    "foundry_metadata": {
                        "project_structure": project_structure,
                        "parsing_failed": True
                    }
                }

            # Update analysis record with static results
            analysis.slither_results = slither_results
            analysis.ai_analysis = parsed_results  # parsed static results
            analysis.status = AnalysisStatus.COMPLETED
            analysis.completed_at = datetime.now(datetime.timezone.utc)()
            await analysis.save()
            
            # Update project status
            project.status = ProjectStatus.COMPLETED
            await project.save()
            
            print("✅ Foundry static analysis completed successfully")
            return analysis
            
        except Exception as e:
            print(f"❌ Foundry static analysis failed: {e}")
            
            # Mark analysis as failed
            analysis.status = AnalysisStatus.FAILED
            analysis.error_message = str(e)
            analysis.completed_at = datetime.now(datetime.timezone.utc)()
            await analysis.save()
            
            # Update project status
            project.status = ProjectStatus.FAILED
            await project.save()
            
            raise e

    async def _perform_single_file_static_analysis(
        self, 
        project: Project, 
        slither_options: Optional[SlitherOptions] = None
    ) -> Analysis:
        """Perform only static analysis step for auditors"""
        
        # Create analysis record
        analysis = Analysis(
            project_id=str(project.id),
            user_id=project.user_id,
            analysis_type=AnalysisType.SLITHER,
            status=AnalysisStatus.RUNNING,
            started_at=datetime.now(datetime.timezone.utc)()
        )
        await analysis.insert()
        
        try:
            # Update project status
            project.status = ProjectStatus.PROCESSING
            project.analysis_id = str(analysis.id)
            await project.save()
            
            # Validate file path
            file_path = Path(project.file_path)
            if not file_path.exists():
                raise Exception(f"Project file not found: {project.file_path}")
            
            print(f"🔄 Starting static analysis for: {file_path}")
                
            # Run static analysis with options
            if slither_options:
                # print(f"📋 Using custom options: {slither_options}")
                slither_results = await self.static_analyzer.run_slither_analysis_with_options(
                    file_path, slither_options
                )
            else:
                # print(f"📋 Using default analysis")
                slither_results = await self.static_analyzer.run_slither_analysis(file_path)
            
            print(f"📊 Slither analysis result: success={slither_results.get('success')}")
        
            if not slither_results.get("success"):
                error_msg = slither_results.get("error", "Unknown Slither error")
                stderr = slither_results.get("stderr", "")

                detailed_error = f"Slither analysis failed: {error_msg}"
                if stderr:
                    detailed_error += f"\nStderr: {stderr}"
                
                print(f"❌ {detailed_error}")
                
                analysis.status = AnalysisStatus.FAILED
                analysis.error_message = detailed_error
                analysis.completed_at = datetime.now(datetime.timezone.utc)()
                await analysis.save()
                
                project.status = ProjectStatus.FAILED
                await project.save()
                
                raise Exception(detailed_error)
            
            try:
                parsed_results = self.static_analyzer.parse_slither_results(slither_results)
                summary = parsed_results.get('summary', {})
                print(f"📊 Vulnerability summary: {summary}")
            
            except Exception as e:
                print(f"Error parsing Slither results: {e}")
                import traceback
                traceback.print_exc()
                # Create empty results but don't fail completely
                parsed_results = {
                    "vulnerabilities": [],
                    "summary": {"total": 0, "high": 0, "medium": 0, "low": 0, "informational": 0},
                    "raw_findings": [],
                    "parsing_error": str(e)
                }

            # Update analysis record with static results only
            analysis.slither_results = slither_results
            analysis.ai_analysis = parsed_results  # parsed static results
            analysis.status = AnalysisStatus.COMPLETED
            analysis.completed_at = datetime.now(datetime.timezone.utc)()
            await analysis.save()
            
            # Update project status
            project.status = ProjectStatus.COMPLETED
            await project.save()
            
            print("✅ Static analysis completed successfully")
            return analysis
            
        except Exception as e:
            print(f"❌ Static analysis failed: {e}")
            
            # Mark analysis as failed
            analysis.status = AnalysisStatus.FAILED
            analysis.error_message = str(e)
            analysis.completed_at = datetime.now(datetime.timezone.utc)()
            await analysis.save()
            
            # Update project status
            project.status = ProjectStatus.FAILED
            await project.save()
            
            raise e
    
# AI enhancement handle & report generation
    async def perform_ai_enhancement(
        self, 
        analysis: Analysis
    ) -> Analysis:
        """Perform AI enhancement on existing static analysis"""
        
        if not analysis.slither_results:
            raise Exception("No static analysis results found to enhance")
        
        try:
            # Update status
            analysis.status = AnalysisStatus.RUNNING
            await analysis.save()
            
            # Get project for source code
            project = await Project.get(analysis.project_id)
            if not project:
                raise Exception("Project not found")
            
            # Handle different project types
            if project.project_type == ProjectType.FOUNDRY_PROJECT:
                # For Foundry projects, use specialized AI analysis
                project_path = Path(project.analysis_path)
                
                # Get project structure
                from app.services.file_service import FileService
                project_structure = FileService.analyze_foundry_project_structure(project_path)
                
                # Get main contract files
                main_contracts = []
                for source_file in project_structure.get("source_files", []):
                    full_path = project_path / source_file
                    if full_path.exists() and not any(skip in str(source_file).lower() for skip in ['test', 'mock', 'lib/']):
                        main_contracts.append(str(full_path))
                
                # Use Foundry-specific AI analysis
                ai_analysis = await self.ai_analyzer.analyze_foundry_project(
                    project_structure, 
                    analysis.slither_results, 
                    main_contracts[:5],  # Limit to 5 files for token limits
                )
            else:
                # Single file analysis
                source_code = await self._read_single_file_safely(project.file_path)
                ai_analysis = await self.ai_analyzer.analyze_vulnerabilities(
                    analysis.slither_results, source_code
                )

            # # Handle different project types
            # if project.project_type == ProjectType.FOUNDRY_PROJECT:
            #     project_path = Path(project.analysis_path)
            #     # actual_project_path = await self._get_foundry_analysis_path(project)
            #     source_code = await self._read_foundry_source_safely(project.analysis_path)
            # else:
            #     source_code = await self._read_single_file_safely(project.file_path)
            
            # Run AI analysis with error handling
            # try:
            #     ai_analysis = await self.ai_analyzer.analyze_vulnerabilities(
            #         analysis.slither_results, source_code
            #     )
            # except Exception as ai_error:
            #     print(f"❌ AI analysis error: {ai_error}")
            #     # Don't fail completely, just add error info
            #     ai_analysis = {
            #         "success": False,
            #         "error": f"AI analysis failed: {str(ai_error)}",
            #         "vulnerabilities": [],
            #         "summary": {"total": 0, "high": 0, "medium": 0, "low": 0, "informational": 0},
            #         "ai_recommendations": [f"AI analysis failed: {str(ai_error)}"]
            #     }

            # Always proceed with results (even if AI failed)
            static_results = analysis.ai_analysis or {}

            if ai_analysis.get("success"):
                # Successful AI enhancement
                enhanced_analysis = {
                    "vulnerabilities": ai_analysis.get("vulnerabilities", static_results.get("vulnerabilities", [])),
                    "summary": ai_analysis.get("summary", static_results.get("summary", {})),
                    "ai_recommendations": ai_analysis.get("ai_recommendations", []),
                    "static_findings": static_results.get("vulnerabilities", []),
                    "ai_enhanced": True 
                }
                
            else:
                # AI failed, but keep static results
                enhanced_analysis = {
                    "vulnerabilities": static_results.get("vulnerabilities", []),
                    "summary": static_results.get("summary", {}),
                    "ai_recommendations": [ai_analysis.get("error", "AI analysis failed")],
                    "static_findings": static_results.get("vulnerabilities", []),
                    "ai_enhanced": False,
                    "ai_error": ai_analysis.get("error")
                }
            
            # Update analysis record
            analysis.ai_analysis = enhanced_analysis
            analysis.status = AnalysisStatus.COMPLETED
            analysis.completed_at = datetime.now(datetime.timezone.utc)()
            await analysis.save()
                
            print("AI enhancement completed successfully")
            return analysis            
        except Exception as e:
            print(f"AI enhancement failed with error: {e}")
            import traceback
            traceback.print_exc()

            # Mark analysis as failed
            analysis.status = AnalysisStatus.FAILED
            analysis.error_message = str(e)
            analysis.completed_at = datetime.now(datetime.timezone.utc)()
            await analysis.save()
            
            raise e
    
    async def generate_analysis_report(
        self, 
        analysis: Analysis, 
        format_type: str = "html"
    ) -> str:
        """Generate report for existing analysis"""
        
        if not analysis.ai_analysis:
            raise Exception("No analysis data available for report generation")
        
        project = await Project.get(analysis.project_id)
        if not project:
            raise Exception("Project not found")
        
        try:
            if format_type == "html":
                report_path = await self.report_generator.generate_html_report(
                    analysis.ai_analysis, project
                )
            elif format_type == "json":
                report_path = await self.report_generator.generate_json_report(
                    analysis.ai_analysis, project
                )
            elif format_type == "markdown":
                report_path = await self.report_generator.generate_markdown_report(
                    analysis.ai_analysis, project
                )
            else:
                raise Exception(f"Unsupported format: {format_type}")
            
            # Update analysis record with report path
            analysis.report_path = report_path
            await analysis.save()
            
            print(f"Report generated successfully: {report_path}")
            return report_path
            
        except Exception as e:
            print(f"Report generation failed: {e}")
            raise e

# Utilities

    async def _read_single_file_safely(self, file_path: str) -> str:
        """Safely read single file source code"""
        try:
            file_path_obj = Path(file_path)
            
            # Try multiple encodings
            encodings = ['utf-8', 'utf-8-sig', 'latin1', 'cp1252']
            
            for encoding in encodings:
                try:
                    with open(file_path_obj, 'r', encoding=encoding) as f:
                        content = f.read()
                    print(f"✅ Successfully read file with {encoding} encoding")
                    return content
                except UnicodeDecodeError:
                    continue
            
            # If all encodings fail, read as binary and handle
            with open(file_path_obj, 'rb') as f:
                binary_content = f.read()
                content = binary_content.decode('utf-8', errors='ignore')
                print("⚠️ Read file with UTF-8 ignoring errors")
                return content
                
        except Exception as e:
            print(f"❌ Error reading single file: {e}")
            raise Exception(f"Could not read source file: {str(e)}")

    async def _read_foundry_source_safely(self, project_path: str) -> str:
        """Safely read Foundry project source files"""
        try:
            project_path_obj = Path(project_path)
            
            # Find source files in Foundry project
            source_files = []
            source_dirs = ['src', 'contracts', 'lib']
            
            for source_dir in source_dirs:
                dir_path = project_path_obj / source_dir
                if dir_path.exists():
                    # Find .sol files
                    sol_files = list(dir_path.rglob('*.sol'))
                    source_files.extend(sol_files)
            
            if not source_files:
                raise Exception("No Solidity source files found in Foundry project")
            
            # ✅ FIX: Read multiple files safely and combine
            combined_source = []
            encodings = ['utf-8', 'utf-8-sig', 'latin1', 'cp1252']
            
            for source_file in source_files[:10]:  # Limit to first 10 files to avoid token limits
                # Skip test files and dependencies
                file_str = str(source_file)
                if any(skip in file_str.lower() for skip in ['test', 'mock', 'lib/', 'node_modules/']):
                    continue
                
                try:
                    file_content = None
                    
                    # Try multiple encodings
                    for encoding in encodings:
                        try:
                            with open(source_file, 'r', encoding=encoding) as f:
                                file_content = f.read()
                            break
                        except UnicodeDecodeError:
                            continue
                    
                    # If all encodings fail, read with error handling
                    if file_content is None:
                        with open(source_file, 'rb') as f:
                            binary_content = f.read()
                            file_content = binary_content.decode('utf-8', errors='ignore')
                    
                    # Add file header and content
                    relative_path = source_file.relative_to(project_path_obj)
                    combined_source.append(f"// FILE: {relative_path}")
                    combined_source.append(file_content)
                    combined_source.append("// END FILE\n")
                    
                except Exception as e:
                    print(f"⚠️ Skipping file {source_file} due to error: {e}")
                    continue
            
            if not combined_source:
                raise Exception("Could not read any source files from Foundry project")
            
            result = "\n".join(combined_source)
            print(f"✅ Successfully combined {len([s for s in combined_source if s.startswith('// FILE:')])} Foundry source files")
            
            # Limit content size for AI processing
            if len(result) > 50000:  # 50KB limit
                result = result[:50000] + "\n\n// ... (content truncated for AI processing)"
            
            return result
            
        except Exception as e:
            print(f"❌ Error reading Foundry project: {e}")
            raise Exception(f"Could not read Foundry project source: {str(e)}")

    async def _get_foundry_analysis_path(self, project: Project) -> Path:
        """Get the actual analysis path for Foundry projects"""
        
        project_path = Path(project.file_path)
        
        if project.project_type == ProjectType.FOUNDRY_PROJECT and project_path.suffix.lower() == '.zip':
            from app.services.file_service import FileService
            extracted_base = FileService.EXTRACTED_DIR
            
            # Find matching extracted directory (look for recent temp directories)
            extracted_dirs = [d for d in extracted_base.iterdir() if d.is_dir() and d.name.startswith('temp_')]
            
            # Find the directory that contains Foundry files
            foundry_project_path = None
            for extracted_dir in sorted(extracted_dirs, key=lambda x: x.stat().st_mtime, reverse=True):
                if FileService.is_foundry_project(extracted_dir):
                    foundry_project_path = extracted_dir
                    break
                
                # Also check subdirectories (in case ZIP contains nested structure)
                for subdir in extracted_dir.iterdir():
                    if subdir.is_dir() and FileService.is_foundry_project(subdir):
                        foundry_project_path = subdir
                        break
                
                if foundry_project_path:
                    break
            
            if not foundry_project_path:
                raise Exception(f"Could not find extracted Foundry project for: {project.file_path}")
            
            print(f"🔄 Using extracted Foundry project path: {foundry_project_path}")
            return foundry_project_path
        
        # For non-ZIP Foundry projects or if already extracted
        if not project_path.exists():
            raise Exception(f"Foundry project path not found: {project.file_path}")
        
        return project_path