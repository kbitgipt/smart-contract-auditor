#!/usr/bin/env python3
import asyncio
import sys
import os
from pathlib import Path

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.static_analyzer import StaticAnalyzer, SlitherOptions

async def compare_methods():
    print("🔍 Comparing API vs Test Script methods...")
    
    # Create same test contract
    test_file = Path("vulnerable_contract.sol")
    contract_code = '''
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract VulnerableContract {
    mapping(address => uint256) public balances;
    address public owner;
    
    constructor() {
        owner = msg.sender;
    }
    
    // Reentrancy vulnerability
    function withdraw(uint256 amount) public {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        
        // Vulnerable call before state update
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Transfer failed");
        
        balances[msg.sender] -= amount;
    }
    
    function deposit() public payable {
        balances[msg.sender] += msg.value;
    }
    
    // Unchecked return value
    function transfer(address to, uint256 amount) public {
        require(balances[msg.sender] >= amount, "Insufficient balance");
        balances[msg.sender] -= amount;
        balances[to] += amount;
        
        // Vulnerable - not checking return value
        to.call{value: amount}("");
    }
}
'''
    
    with open(test_file, 'w') as f:
        f.write(contract_code)
    
    analyzer = StaticAnalyzer()
    
    print("\n" + "="*60)
    print("🧪 METHOD 1: run_slither_analysis() (Test Script)")
    print("="*60)
    
    result1 = await analyzer.run_slither_analysis(test_file)
    print(f"✅ Success: {result1.get('success')}")
    print(f"📊 Return code: {result1.get('return_code')}")
    
    if result1.get('data'):
        print(f"🔑 Data keys: {list(result1['data'].keys())}")
        if 'results' in result1['data']:
            print(f"🔑 Results keys: {list(result1['data']['results'].keys())}")
            if 'detectors' in result1['data']['results']:
                detectors = result1['data']['results']['detectors']
                print(f"🐛 Found {len(detectors)} detectors")
    
    parsed1 = analyzer.parse_slither_results(result1)
    print(f"📈 Parsed vulnerabilities: {len(parsed1['vulnerabilities'])}")
    print(f"📊 Summary: {parsed1['summary']}")
    
    print("\n" + "="*60)
    print("🌐 METHOD 2: run_slither_analysis_with_options() (API)")
    print("="*60)
    
    # Simulate API call with default options
    options = SlitherOptions()
    result2 = await analyzer.run_slither_analysis_with_options(test_file, options)
    print(f"✅ Success: {result2.get('success')}")
    print(f"📊 Return code: {result2.get('return_code')}")
    
    if result2.get('data'):
        print(f"🔑 Data keys: {list(result2['data'].keys())}")
        if 'results' in result2['data']:
            print(f"🔑 Results keys: {list(result2['data']['results'].keys())}")
            if 'detectors' in result2['data']['results']:
                detectors = result2['data']['results']['detectors']
                print(f"🐛 Found {len(detectors)} detectors")
    
    parsed2 = analyzer.parse_slither_results(result2)
    print(f"📈 Parsed vulnerabilities: {len(parsed2['vulnerabilities'])}")
    print(f"📊 Summary: {parsed2['summary']}")
    
    print("\n" + "="*60)
    print("🔍 COMPARISON")
    print("="*60)
    print(f"Method 1 vulnerabilities: {len(parsed1['vulnerabilities'])}")
    print(f"Method 2 vulnerabilities: {len(parsed2['vulnerabilities'])}")
    
    if len(parsed1['vulnerabilities']) != len(parsed2['vulnerabilities']):
        print("❌ MISMATCH DETECTED!")
        
        print("\n📄 Raw output comparison:")
        print("Method 1 raw output (first 500 chars):")
        print(result1.get('raw_output', 'None')[:500])
        print("\nMethod 2 raw output (first 500 chars):")
        print(result2.get('raw_output', 'None')[:500])
        
        print("\n🔧 Command comparison:")
        # Method 1 uses basic command
        print("Method 1 command: slither file --json - --disable-color --solc-disable-warnings")
        
        # Method 2 uses options
        print("Method 2 command: slither file --json - --exclude-dependencies --disable-color --solc-disable-warnings")
        
    else:
        print("✅ Both methods return same number of vulnerabilities")
    
    # Cleanup
    if test_file.exists():
        test_file.unlink()
        print(f"\n🗑️ Cleaned up test file")

if __name__ == "__main__":
    asyncio.run(compare_methods())