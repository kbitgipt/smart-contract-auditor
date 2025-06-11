# System support smart contract auditing with AI integration
## Run local

### Backend

```
cd backend/

python -m venv venv 

source venv/bin/activate

pip install --no-cache-dir -r requirements.txt

uvicorn app.main:app --reload --port 9000
```

### Frontend

```
cd frontend

npm install

npm run dev

# Docker run
```

## Docker

```
cd smart-contract-auditor
chmod +x run-docker.sh
./run-docker.sh

or docker-compose up --build

# clean up
chmod +x clean-docker.sh
./clean-docker.sh
```


bạn hãy đưa ra các chỉnh sửa cần thiết để dùng assistant có sẵn:
- lần đầu upload file source code của project/single và analysis report tới assistant, về sau khi người phân tích lại thì không cần upload file souce code nữa, mà dùng prompt để refer đến file source đó còn file static analysis thì upload cái mới nhất của project đó.
- assistant tôi đã tạo đã có response format và instructions:
{"type": "object",
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
            "required": ["vulnerabilities", "summary", "general_recommendations"]}
Instructions:
`You are an expert smart contract security auditor. Analyze uploaded Solidity contracts and Slither static analysis results to provide comprehensive security assessments.

Use code interpreter to:
- Analyze source code patterns and logic flows
- Cross-reference findings with actual code

Use file search to:
- Examine Slither output structure and findings
- Extract specific vulnerability details
- Correlate static analysis results with source code

Provide detailed, actionable security recommendations with specific code examples and remediation steps.`