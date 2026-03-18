#!/usr/bin/env python3
"""
Start the backend server to test if everything works
"""

import os
import sys

def start_backend():
    """Start the FastAPI backend server"""
    
    # Change to backend directory  
    backend_dir = r"c:\Users\anish\OneDrive\Desktop\bio med\Sensory-Flow\backend"
    os.chdir(backend_dir)
    
    print(f"Starting backend from: {backend_dir}")
    
    try:
        # Import and run the app
        from main import app
        
        print("✅ FastAPI app loaded successfully!")
        print("Backend is ready to process videos.")
        
        # Start the server
        import uvicorn
        print("\n🚀 Starting server on http://localhost:8000")
        print("Available endpoints:")
        print("  - GET  / (health check)")
        print("  - POST /api/upload-video")
        print("  - POST /api/process-exercise/{exercise_id}")
        print("  - POST /api/process-exercise-files/{exercise_id}")
        
        print("\nExercise types supported:")
        from main import EXERCISE_ID_TO_ASSESSMENT_KEY
        for exercise_id in EXERCISE_ID_TO_ASSESSMENT_KEY.keys():
            print(f"  - {exercise_id}")
        
        print("\n💡 You can now test with tools like Postman or curl")
        print("Example: POST to /api/process-exercise-files/jumping_jacks")
        
        # Start the server
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
        
    except Exception as e:
        print(f"❌ Failed to start backend: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    start_backend()