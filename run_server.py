#!/usr/bin/env python
"""Simple Flask server launcher"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from app import app

if __name__ == '__main__':
    print("Starting Flask server...")
    try:
        app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
    except Exception as e:
        print(f"Error starting server: {e}")
        import traceback
        traceback.print_exc()
