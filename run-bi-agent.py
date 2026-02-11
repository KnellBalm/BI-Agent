#!/usr/bin/env python3.14
"""
Local BI-Agent runner script
Bypasses the installed bi-agent command to use the latest source code
"""
import sys
import os

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Import and run the console
from backend.orchestrator.bi_agent_console import run_app

if __name__ == '__main__':
    sys.exit(run_app())
