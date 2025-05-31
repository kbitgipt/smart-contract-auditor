#!/usr/bin/env python3
import asyncio
import os
import sys
from pathlib import Path

# Add current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.static_analyzer import StaticAnalyzer

async def test_slither():
    print("Testing Slither integration...")
    
    # Test với file vulnerable_contract.sol có sẵn
    test_file = Path("vulnerable_contract.sol")
    
    if not test_file.exists():
        # Tạo file test contract
        with open(test_file, 'w') as f:
            f.write("""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract VulnerableContract {
    address public owner;
    mapping(address => uint256) public balances;
    
    constructor() {
        owner = msg.sender;
    }
    
    // Reentrancy vulnerability
    function withdraw(uint256 amount) public {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        
        // Vulnerable: External call before state change
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Transfer failed");
        
        // State change after external call - DANGEROUS!
        balances[msg.sender] -= amount;
    }
    
    function deposit() public payable {
        balances[msg.sender] += msg.value;
    }
}
""")
        print(f"Created test file: {test_file}")
    
    analyzer = StaticAnalyzer()
    
    # Test version detection
    version = analyzer.detect_solidity_version(test_file)
    print(f"Detected Solidity version: {version}")
    print(f"Is supported: {analyzer.is_supported_solidity_version(version)}")
    
    # Test Slither analysis
    print("\nRunning Slither analysis...")
    result = await analyzer.run_slither_analysis(test_file)
    
    print(f"Analysis result: {result}")
    
    if result.get("success"):
        print("✅ Slither analysis successful!")
        
        # Parse results
        parsed = analyzer.parse_slither_results(result)
        print(f"Parsed vulnerabilities: {len(parsed['vulnerabilities'])}")
        print(f"Summary: {parsed['summary']}")
        
        for vuln in parsed['vulnerabilities']:
            print(f"- {vuln['title']} ({vuln['severity']})")
    else:
        print("❌ Slither analysis failed!")
        print(f"Error: {result.get('error')}")
        if 'stderr' in result:
            print(f"Stderr: {result['stderr']}")
        if 'stdout' in result:
            print(f"Stdout: {result['stdout']}")
    
    # Cleanup
    if test_file.exists():
        test_file.unlink()
        print(f"Cleaned up test file: {test_file}")

if __name__ == "__main__":
    asyncio.run(test_slither())