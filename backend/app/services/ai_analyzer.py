import os
import json
from typing import Dict, List
from openai import AsyncOpenAI

class AIAnalyzer:
    """Service for AI-powered vulnerability analysis using OpenAI"""
    
    def __init__(self):
        self.openai_client = AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY")
        )
    
    async def analyze_vulnerabilities(self, slither_results: Dict, source_code: str) -> Dict:
        """Analyze Slither results with OpenAI for better categorization and recommendations"""
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
            
            # Prepare prompt for OpenAI
            prompt = self._create_analysis_prompt(detectors, source_code)
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-nano",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert smart contract security auditor. Analyze the provided Slither output and provide detailed vulnerability analysis with severity classification and remediation recommendations."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=4000
            )
            
            # Parse OpenAI response
            ai_analysis = self._parse_ai_response(response.choices[0].message.content)
            
            return {
                "success": True,
                "vulnerabilities": ai_analysis.get("vulnerabilities", []),
                "summary": ai_analysis.get("summary", {}),
                "ai_recommendations": ai_analysis.get("general_recommendations", [])
            }
            
        except Exception as e:
            print(f"OpenAI analysis error: {e}")
            return {
                "success": False,
                "error": f"AI analysis failed: {str(e)}"
            }
    
    def _create_analysis_prompt(self, detectors: List[Dict], source_code: str) -> str:
        """Create structured prompt for OpenAI analysis"""
        
        prompt = f"""
Please analyze the following smart contract security findings from Slither static analysis tool.

**SOURCE CODE:**
```solidity
{source_code[:3000]}...
```

**SLITHER FINDINGS:**
{json.dumps(detectors, indent=2)}

**ANALYSIS REQUIREMENTS:**
1. For each finding, provide:
   - Clear vulnerability description
   - Severity level (HIGH/MEDIUM/LOW/INFORMATIONAL)
   - Specific remediation recommendations
   - Code examples if applicable

2. Severity Classification Guidelines:
   - HIGH: Direct loss of funds, unauthorized access, critical business logic flaws
   - MEDIUM: Potential loss of funds, access control issues, state manipulation
   - LOW: Best practice violations, minor logic issues, optimization opportunities
   - INFORMATIONAL: Code quality, documentation, style improvements

3. Response Format (JSON):
```json
{{
  "vulnerabilities": [
    {{
      "id": "unique_id",
      "title": "Vulnerability Title",
      "description": "Detailed description",
      "severity": "HIGH|MEDIUM|LOW|INFORMATIONAL",
      "impact": "Potential impact description",
      "recommendation": "Specific fix recommendation",
      "code_snippet": "Relevant code if applicable",
      "references": ["Additional resources"]
    }}
  ],
  "summary": {{
    "total": 0,
    "high": 0,
    "medium": 0,
    "low": 0,
    "informational": 0
  }},
  "general_recommendations": [
    "Overall security recommendations"
  ]
}}
```

Focus on providing actionable, specific recommendations that developers can implement immediately.
"""
        return prompt
    
    def _parse_ai_response(self, response_content: str) -> Dict:
        """Parse and validate OpenAI response"""
        try:
            # Extract JSON from response
            json_start = response_content.find('{')
            json_end = response_content.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response_content[json_start:json_end]
                analysis = json.loads(json_str)
                
                # Validate structure
                if "vulnerabilities" in analysis and "summary" in analysis:
                    return analysis
            
            # If JSON parsing fails, create structured response from text
            return self._extract_from_text_response(response_content)
            
        except Exception as e:
            print(f"Error parsing OpenAI response: {e}")
            return {
                "vulnerabilities": [],
                "summary": {"total": 0, "high": 0, "medium": 0, "low": 0, "informational": 0},
                "general_recommendations": ["Unable to parse AI analysis. Please review Slither output manually."]
            }
    
    def _extract_from_text_response(self, text: str) -> Dict:
        """Extract vulnerability info from text response if JSON parsing fails"""
        vulnerabilities = []
        summary = {"total": 0, "high": 0, "medium": 0, "low": 0, "informational": 0}
        
        # Simple text parsing for vulnerabilities
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if 'HIGH' in line.upper():
                summary["high"] += 1
                summary["total"] += 1
            elif 'MEDIUM' in line.upper():
                summary["medium"] += 1
                summary["total"] += 1
            elif 'LOW' in line.upper():
                summary["low"] += 1
                summary["total"] += 1
            elif 'INFORMATIONAL' in line.upper():
                summary["informational"] += 1
                summary["total"] += 1
        
        return {
            "vulnerabilities": vulnerabilities,
            "summary": summary,
            "general_recommendations": ["AI analysis completed with text parsing fallback."]
        }
    
    async def enhance_vulnerability_analysis(self, vulnerability: Dict, source_code: str) -> Dict:
        """Enhance individual vulnerability with more detailed AI analysis"""
        try:
            prompt = f"""
Analyze this specific vulnerability in detail:

**VULNERABILITY:**
{json.dumps(vulnerability, indent=2)}

**SOURCE CODE CONTEXT:**
```solidity
{source_code[:2000]}...
```

Provide:
1. Detailed explanation of the vulnerability
2. Step-by-step exploitation scenario
3. Specific code fix with before/after examples
4. Prevention strategies

Response in JSON format with enhanced details.
"""
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-nano",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a smart contract security expert. Provide detailed vulnerability analysis."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=2000
            )
            
            return {
                "success": True,
                "enhanced_analysis": response.choices[0].message.content
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Enhancement failed: {str(e)}"
            }