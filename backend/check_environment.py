#!/usr/bin/env python3
import subprocess
import sys
import os
from pathlib import Path

def check_command(cmd):
    """Check if a command is available"""
    try:
        result = subprocess.run([cmd, '--version'], 
                              capture_output=True, 
                              text=True, 
                              timeout=10)
        return result.returncode == 0, result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False, "Command not found"

def check_python_packages():
    """Check required Python packages"""
    packages = ['slither-analyzer']
    for package in packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package} is installed")
        except ImportError:
            print(f"❌ {package} is NOT installed")

def check_environment():
    print("=== Environment Check ===")
    
    # Check Python version
    print(f"Python version: {sys.version}")
    
    # Check current working directory
    print(f"Current directory: {os.getcwd()}")
    
    # Check PATH
    print(f"PATH: {os.environ.get('PATH', 'Not set')}")
    
    # Check virtual environment
    venv = os.environ.get('VIRTUAL_ENV')
    if venv:
        print(f"Virtual environment: {venv}")
    else:
        print("❌ No virtual environment detected")
    
    print("\n=== Command Check ===")
    
    # Check Slither
    slither_ok, slither_out = check_command('slither')
    if slither_ok:
        print(f"✅ Slither: {slither_out}")
    else:
        print(f"❌ Slither: {slither_out}")
        
        # Try alternative paths
        possible_paths = [
            'slither-analyzer',
            os.path.expanduser('~/.local/bin/slither'),
            '/usr/local/bin/slither',
            str(Path(sys.executable).parent / 'slither')
        ]
        
        for path in possible_paths:
            if Path(path).exists():
                print(f"Found Slither at: {path}")
                break
    
    # Check Solc
    solc_ok, solc_out = check_command('solc')
    if solc_ok:
        print(f"✅ Solc: {solc_out}")
    else:
        print(f"❌ Solc: {solc_out}")
    
    print("\n=== Python Packages ===")
    check_python_packages()
    
    print("\n=== Recommendations ===")
    if not slither_ok:
        print("Install Slither with: pip install slither-analyzer")
    if not solc_ok:
        print("Install Solc with: pip install py-solc-x")

if __name__ == "__main__":
    check_environment()