#!/usr/bin/env python
"""Debug server starter - for testing Flask without reloader"""

import sys
import traceback

print("Step 1: Starting debug server...")

try:
    print("Step 2: Importing Flask app...")
    from app import app
    print("Step 3: App imported successfully")
    
    print("Step 4: Starting Flask server...")
    app.run(debug=False, host='127.0.0.1', port=5000, use_reloader=False)
    
except KeyboardInterrupt:
    print("\nServer stopped by user")
    sys.exit(0)
except Exception as e:
    print(f"ERROR in server startup: {e}")
    print("\nFull traceback:")
    traceback.print_exc()
    sys.exit(1)
