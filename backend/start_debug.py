#!/usr/bin/env python3
import subprocess
import sys
import os
import socket
from pathlib import Path

def check_port(port):
    """Check if port is available"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        result = s.connect_ex(('localhost', port))
        return result != 0  # True if port is available

def main():
    print("=== AuditSmart Backend Debug Startup ===")
    
    # Check current directory
    print(f"Current directory: {os.getcwd()}")
    
    # Check if we're in the right directory
    if not Path("app/main.py").exists():
        print("❌ Error: app/main.py not found!")
        print("Please run this script from the backend directory")
        sys.exit(1)
    
    # Check port availability
    port = 8000
    if not check_port(port):
        print(f"❌ Port {port} is already in use!")
        print("Please kill the process using this port or use a different port")
        sys.exit(1)
    else:
        print(f"✅ Port {port} is available")
    
    # Check environment
    print(f"Python executable: {sys.executable}")
    print(f"Python version: {sys.version}")
    
    # Check virtual environment
    venv = os.environ.get('VIRTUAL_ENV')
    if venv:
        print(f"✅ Virtual environment: {venv}")
    else:
        print("⚠️  No virtual environment detected")
    
    # Set environment variables
    os.environ["PYTHONPATH"] = os.getcwd()
    
    # Start server with debug info
    cmd = [
        sys.executable, "-m", "uvicorn", 
        "app.main:app",
        "--reload",
        "--host", "0.0.0.0",
        "--port", str(port),
        "--log-level", "debug"
    ]
    
    print(f"Starting server with command: {' '.join(cmd)}")
    print("=" * 50)
    
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"❌ Server failed to start: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()