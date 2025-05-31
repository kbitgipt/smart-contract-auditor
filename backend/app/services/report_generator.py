import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from app.models.project import Project

class ReportGenerator:
    """Service for generating various report formats"""
    
    def __init__(self):
        self.reports_dir = Path("reports")
        self.reports_dir.mkdir(exist_ok=True)
    
    async def generate_html_report(self, analysis_data: Dict, project: Project) -> str:
        """Generate comprehensive HTML report"""
        
        vulnerabilities = analysis_data.get("vulnerabilities", [])
        summary = analysis_data.get("summary", {})
        ai_recommendations = analysis_data.get("ai_recommendations", [])
        
        # Generate HTML content
        html_content = self._create_html_template(vulnerabilities, summary, ai_recommendations, project)
        
        # Save to file
        report_filename = f"report_{project.id}_{int(datetime.utcnow().timestamp())}.html"
        report_path = self.reports_dir / report_filename
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return str(report_path)
    
    async def generate_json_report(self, analysis_data: Dict, project: Project) -> str:
        """Generate JSON report for API consumption"""
        
        report_data = {
            "project": {
                "id": str(project.id),
                "name": project.name,
                "description": project.description,
                "file_name": project.original_filename,
                "file_size": project.file_size,
                "project_type": project.project_type.value,
                "created_at": project.created_at.isoformat()
            },
            "analysis": {
                "timestamp": datetime.utcnow().isoformat(),
                "tools_used": ["Slither", "OpenAI GPT-4"],
                "summary": analysis_data.get("summary", {}),
                "vulnerabilities": analysis_data.get("vulnerabilities", []),
                "ai_recommendations": analysis_data.get("ai_recommendations", [])
            },
            "metadata": {
                "report_version": "1.0",
                "generated_by": "AuditSmart Platform",
                "report_id": hashlib.md5(f"{project.id}_{datetime.utcnow().isoformat()}".encode()).hexdigest()[:8]
            }
        }
        
        # Save JSON report
        import json
        report_filename = f"report_{project.id}_{int(datetime.utcnow().timestamp())}.json"
        report_path = self.reports_dir / report_filename
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        return str(report_path)
    
    async def generate_markdown_report(self, analysis_data: Dict, project: Project) -> str:
        """Generate Markdown report"""
        
        vulnerabilities = analysis_data.get("vulnerabilities", [])
        summary = analysis_data.get("summary", {})
        ai_recommendations = analysis_data.get("ai_recommendations", [])
        
        markdown_content = f"""# Security Analysis Report

**Project:** {project.name}  
**File:** {project.original_filename}  
**Analysis Date:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC  
**Tools Used:** Slither + OpenAI GPT-4  

## Summary

| Severity | Count |
|----------|-------|
| High | {summary.get('high', 0)} |
| Medium | {summary.get('medium', 0)} |
| Low | {summary.get('low', 0)} |
| Informational | {summary.get('informational', 0)} |
| **Total** | **{summary.get('total', 0)}** |

## Vulnerabilities

"""
        
        if vulnerabilities:
            for i, vuln in enumerate(vulnerabilities, 1):
                severity_emoji = {
                    "HIGH": "🔴",
                    "MEDIUM": "🟡", 
                    "LOW": "🟢",
                    "INFORMATIONAL": "ℹ️"
                }.get(vuln.get('severity', 'INFORMATIONAL'), 'ℹ️')
                
                markdown_content += f"""### {i}. {vuln.get('title', 'Unknown Issue')} {severity_emoji}

**Severity:** {vuln.get('severity', 'Unknown')}  
**Impact:** {vuln.get('impact', 'Unknown impact')}

**Description:**  
{vuln.get('description', 'No description available')}

**Recommendation:**  
{vuln.get('recommendation', 'No specific recommendation available')}

"""
                if vuln.get('code_snippet'):
                    markdown_content += f"""**Code Snippet:**
```solidity
{vuln.get('code_snippet')}
```

"""
        else:
            markdown_content += "🎉 No vulnerabilities detected! Your contract appears to be secure.\n\n"
        
        # Add AI recommendations
        if ai_recommendations:
            markdown_content += "## AI Security Recommendations\n\n"
            for rec in ai_recommendations:
                markdown_content += f"- {rec}\n"
            markdown_content += "\n"
        
        markdown_content += f"""---
*Generated by AuditSmart Platform*  
*Report ID: {hashlib.md5(f"{project.id}_{datetime.utcnow().isoformat()}".encode()).hexdigest()[:8]}*
"""
        
        # Save markdown report
        report_filename = f"report_{project.id}_{int(datetime.utcnow().timestamp())}.md"
        report_path = self.reports_dir / report_filename
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        return str(report_path)
    
    def _create_html_template(self, vulnerabilities: List[Dict], summary: Dict, ai_recommendations: List[str], project: Project) -> str:
        """Create HTML template for the report"""
        
        html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Security Analysis Report - {project.name}</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 8px 8px 0 0; }}
        .header h1 {{ margin: 0; font-size: 2.5em; }}
        .header p {{ margin: 10px 0 0 0; opacity: 0.9; }}
        .content {{ padding: 30px; }}
        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .summary-card {{ background: #f8f9fa; border-radius: 8px; padding: 20px; text-align: center; border-left: 4px solid; }}
        .summary-card.high {{ border-left-color: #dc3545; }}
        .summary-card.medium {{ border-left-color: #fd7e14; }}
        .summary-card.low {{ border-left-color: #ffc107; }}
        .summary-card.info {{ border-left-color: #17a2b8; }}
        .summary-card h3 {{ margin: 0 0 10px 0; font-size: 2em; }}
        .vulnerability {{ background: #fff; border: 1px solid #dee2e6; border-radius: 8px; margin-bottom: 20px; overflow: hidden; }}
        .vulnerability-header {{ padding: 15px 20px; border-bottom: 1px solid #dee2e6; }}
        .vulnerability-body {{ padding: 20px; }}
        .severity {{ display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 0.8em; font-weight: bold; text-transform: uppercase; }}
        .severity.high {{ background: #dc3545; color: white; }}
        .severity.medium {{ background: #fd7e14; color: white; }}
        .severity.low {{ background: #ffc107; color: black; }}
        .severity.informational {{ background: #17a2b8; color: white; }}
        .code-block {{ background: #f8f9fa; border: 1px solid #e9ecef; border-radius: 4px; padding: 15px; margin: 10px 0; font-family: 'Courier New', monospace; font-size: 0.9em; overflow-x: auto; }}
        .recommendations {{ background: #e7f3ff; border: 1px solid #b8daff; border-radius: 8px; padding: 20px; margin: 20px 0; }}
        .footer {{ background: #f8f9fa; padding: 20px; border-radius: 0 0 8px 8px; text-align: center; color: #6c757d; }}
        .meta-info {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; margin-bottom: 30px; }}
        .meta-card {{ background: #f8f9fa; padding: 15px; border-radius: 6px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Security Analysis Report</h1>
            <p>Generated for: {project.name}</p>
        </div>
        
        <div class="content">
            <div class="meta-info">
                <div class="meta-card">
                    <strong>Project:</strong> {project.name}<br>
                    <strong>File:</strong> {project.original_filename}<br>
                    <strong>Size:</strong> {project.file_size / 1024:.1f} KB
                </div>
                <div class="meta-card">
                    <strong>Analysis Date:</strong> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC<br>
                    <strong>Tools Used:</strong> Slither + OpenAI GPT-4<br>
                    <strong>Type:</strong> {project.project_type.value}
                </div>
            </div>
            
            <h2>Summary</h2>
            <div class="summary">
                <div class="summary-card high">
                    <h3>{summary.get('high', 0)}</h3>
                    <p>High Risk</p>
                </div>
                <div class="summary-card medium">
                    <h3>{summary.get('medium', 0)}</h3>
                    <p>Medium Risk</p>
                </div>
                <div class="summary-card low">
                    <h3>{summary.get('low', 0)}</h3>
                    <p>Low Risk</p>
                </div>
                <div class="summary-card info">
                    <h3>{summary.get('informational', 0)}</h3>
                    <p>Informational</p>
                </div>
            </div>
            
            <h2>Vulnerabilities</h2>
"""

        # Add vulnerabilities
        if vulnerabilities:
            for vuln in vulnerabilities:
                severity_class = vuln.get('severity', 'informational').lower()
                html_template += f"""
            <div class="vulnerability">
                <div class="vulnerability-header">
                    <h3>{vuln.get('title', 'Unknown Issue')} 
                        <span class="severity {severity_class}">{vuln.get('severity', 'Unknown')}</span>
                    </h3>
                </div>
                <div class="vulnerability-body">
                    <p><strong>Description:</strong> {vuln.get('description', 'No description available')}</p>
                    <p><strong>Impact:</strong> {vuln.get('impact', 'Unknown impact')}</p>
                    
                    {f'<div class="code-block">{vuln.get("code_snippet", "")}</div>' if vuln.get('code_snippet') else ''}
                    
                    <div class="recommendations">
                        <strong>Recommendation:</strong><br>
                        {vuln.get('recommendation', 'No specific recommendation available')}
                    </div>
                </div>
            </div>
"""
        else:
            html_template += """
            <div class="vulnerability">
                <div class="vulnerability-body">
                    <p style="text-align: center; color: #28a745; font-size: 1.2em;">
                        🎉 No vulnerabilities detected! Your contract appears to be secure.
                    </p>
                </div>
            </div>
"""

        # Add AI recommendations
        if ai_recommendations:
            html_template += """
            <h2>AI Security Recommendations</h2>
            <div class="recommendations">
                <ul>
"""
            for rec in ai_recommendations:
                html_template += f"<li>{rec}</li>"
            
            html_template += """
                </ul>
            </div>
"""

        # Close HTML
        html_template += f"""
        </div>
        
        <div class="footer">
            <p>Generated by AuditSmart Platform | 
               Report ID: {hashlib.md5(f"{project.id}_{datetime.utcnow().isoformat()}".encode()).hexdigest()[:8]} | 
               © 2024 AuditSmart</p>
        </div>
    </div>
</body>
</html>
"""
        return html_template