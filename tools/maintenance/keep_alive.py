#!/usr/bin/env python
"""Flask server with auto-restart"""
import subprocess
import sys
import time
import os

os.chdir(r'c:\Users\USER\Documents\GitHub\jr')

while True:
    print("\n" + "="*60)
    print(f"Starting Flask at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60 + "\n")
    
    try:
        # Run Flask and keep it running
        subprocess.run([sys.executable, 'run_server.py'], check=False)
        
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n\nFlask stopped, restarting in 5 seconds...")
    time.sleep(5)
