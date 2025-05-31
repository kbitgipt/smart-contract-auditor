import asyncio
from pathlib import Path
from app.services.static_analyzer import StaticAnalyzer
from app.services.ai_analyzer import AIAnalyzer
from app.services.report_generator import ReportGenerator

async def test_services():
    # Test Static Analyzer
    analyzer = StaticAnalyzer()
    
    # Test Solidity version detection
    test_sol = Path("test_contract.sol")
    with open(test_sol, 'w') as f:
        f.write("""
pragma solidity ^0.8.0;

contract Test {
    address public owner;
    
    constructor() {
        owner = msg.sender;
    }
}
""")
    
    version = analyzer.detect_solidity_version(test_sol)
    print(f"Detected version: {version}")
    print(f"Is supported: {analyzer.is_supported_solidity_version(version)}")
    
    # Clean up
    test_sol.unlink()

if __name__ == "__main__":
    asyncio.run(test_services())