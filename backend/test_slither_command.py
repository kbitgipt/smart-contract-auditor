#!/usr/bin/env python3
import asyncio
import sys
import os
from pathlib import Path

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.static_analyzer import StaticAnalyzer, SlitherOptions

async def test_api_vs_script_context():
    """Test with same conditions as API vs Script"""
    
    analyzer = StaticAnalyzer()
    
    print("="*60)
    print("🧪 TEST 1: Script-like context (backend/)")
    print("="*60)
    
    # Test 1: Same as script - file in backend/
    script_file = Path("test_script_context.sol")
    
    contract_code = '''
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract VulnerableContract {
    mapping(address => uint256) public balances;
    
    function withdraw(uint256 amount) public {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Transfer failed");
        balances[msg.sender] -= amount;
    }
}
'''
    
    with open(script_file, 'w') as f:
        f.write(contract_code)
    
    print(f"📍 Script context file: {script_file.absolute()}")
    print(f"📍 Current working dir: {os.getcwd()}")
    
    result1 = await analyzer.run_slither_analysis(script_file)
    parsed1 = analyzer.parse_slither_results(result1)
    print(f"✅ Script context vulnerabilities: {len(parsed1['vulnerabilities'])}")
    
    script_file.unlink()
    
    print("\n" + "="*60)
    print("🌐 TEST 2: API-like context (uploads/)")
    print("="*60)
    
    # Test 2: Same as API - file in uploads/
    upload_dir = Path("uploads/test_project")
    upload_dir.mkdir(parents=True, exist_ok=True)
    api_file = upload_dir / "test_api_context.sol"
    
    with open(api_file, 'w') as f:
        f.write(contract_code)
    
    print(f"📍 API context file: {api_file.absolute()}")
    print(f"📍 File parent dir: {api_file.parent}")
    
    # Test with default options (like API does)
    options = SlitherOptions(exclude_dependencies=True)
    result2 = await analyzer.run_slither_analysis_with_options(api_file, options)
    parsed2 = analyzer.parse_slither_results(result2)
    print(f"✅ API context vulnerabilities: {len(parsed2['vulnerabilities'])}")
    
    print("\n" + "="*60)
    print("🔍 COMPARISON")
    print("="*60)
    print(f"Script context: {len(parsed1['vulnerabilities'])} vulnerabilities")
    print(f"API context: {len(parsed2['vulnerabilities'])} vulnerabilities")
    
    if len(parsed1['vulnerabilities']) != len(parsed2['vulnerabilities']):
        print("❌ CONTEXT MISMATCH DETECTED!")
        print(f"Script raw output: {result1.get('raw_output', 'None')[:300]}")
        print(f"API raw output: {result2.get('raw_output', 'None')[:300]}")
    else:
        print("✅ Both contexts return same results")
    
    # Cleanup
    import shutil
    # shutil.rmtree("uploads", ignore_errors=True)

if __name__ == "__main__":
    asyncio.run(test_api_vs_script_context())