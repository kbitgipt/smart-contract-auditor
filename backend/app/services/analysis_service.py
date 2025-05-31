from datetime import datetime
from pathlib import Path
from typing import Dict
from app.models.analysis import Analysis, AnalysisStatus, AnalysisType
from app.models.project import Project, ProjectType, ProjectStatus
from app.services.static_analyzer import StaticAnalyzer
from app.services.ai_analyzer import AIAnalyzer
from app.services.report_generator import ReportGenerator

class AnalysisService:
    """Main orchestrator for smart contract analysis"""
    
    def __init__(self):
        self.static_analyzer = StaticAnalyzer()
        self.ai_analyzer = AIAnalyzer()
        self.report_generator = ReportGenerator()
    
    async def perform_full_analysis(self, project: Project) -> Analysis:
        """Perform complete analysis workflow for a project"""
        
        # Create analysis record
        analysis = Analysis(
            project_id=str(project.id),
            user_id=project.user_id,
            analysis_type=AnalysisType.SLITHER,
            status=AnalysisStatus.RUNNING,
            started_at=datetime.utcnow()
        )
        await analysis.insert()
        
        try:
            # Update project status
            project.status = ProjectStatus.PROCESSING
            project.analysis_id = str(analysis.id)
            await project.save()
            
            # Step 1: Read source code
            with open(project.file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
            
            # Step 2: Validate Solidity version for single files
            if project.project_type == ProjectType.SINGLE_FILE:
                detected_version = self.static_analyzer.detect_solidity_version(Path(project.file_path))
                if not self.static_analyzer.is_supported_solidity_version(detected_version):
                    raise Exception(f"Unsupported Solidity version: {detected_version}. Supported versions: {', '.join(self.static_analyzer.SUPPORTED_SOLC_VERSIONS[:10])}...")
            
            # Step 3: Run static analysis
            slither_results = await self.static_analyzer.run_slither_analysis(Path(project.file_path))
            
            if not slither_results.get("success"):
                raise Exception(f"Slither analysis failed: {slither_results.get('error')}")
            
            # Step 4: Parse static analysis results
            parsed_results = self.static_analyzer.parse_slither_results(slither_results)
            
            # Step 5: Enhance with AI analysis
            ai_analysis = await self.ai_analyzer.analyze_vulnerabilities(slither_results, source_code)
            
            if not ai_analysis.get("success"):
                # Fallback to parsed static results
                final_analysis = parsed_results
                final_analysis["ai_recommendations"] = ["AI analysis failed. Using static analysis only."]
            else:
                # Merge AI analysis with static results
                final_analysis = {
                    "vulnerabilities": ai_analysis.get("vulnerabilities", parsed_results["vulnerabilities"]),
                    "summary": ai_analysis.get("summary", parsed_results["summary"]),
                    "ai_recommendations": ai_analysis.get("ai_recommendations", [])
                }
            
            # Step 6: Generate reports
            html_report_path = await self.report_generator.generate_html_report(final_analysis, project)
            json_report_path = await self.report_generator.generate_json_report(final_analysis, project)
            md_report_path = await self.report_generator.generate_markdown_report(final_analysis, project)
            
            # Step 7: Update analysis record
            analysis.status = AnalysisStatus.COMPLETED
            analysis.slither_results = slither_results
            analysis.ai_analysis = final_analysis
            analysis.report_path = html_report_path
            analysis.completed_at = datetime.utcnow()
            await analysis.save()
            
            # Step 8: Update project status
            project.status = ProjectStatus.COMPLETED
            await project.save()
            
            return analysis
            
        except Exception as e:
            # Mark analysis as failed
            analysis.status = AnalysisStatus.FAILED
            analysis.error_message = str(e)
            analysis.completed_at = datetime.utcnow()
            await analysis.save()
            
            # Update project status
            project.status = ProjectStatus.FAILED
            await project.save()
            
            raise e
    
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