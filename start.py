"""
Project Rakshak — Startup Script
Kills any existing node/python server on port 3000, then starts
the FastAPI backend with Uvicorn.
"""
import subprocess
import sys
import os
import signal

PORT = 3000

def kill_port(port: int):
    """Kill any process listening on the given port (Windows + Unix)."""
    try:
        if os.name == "nt":
            result = subprocess.run(
                f"netstat -ano | findstr :{port}",
                shell=True, capture_output=True, text=True
            )
            for line in result.stdout.strip().splitlines():
                parts = line.split()
                if len(parts) >= 5 and f":{port}" in parts[1]:
                    pid = parts[-1]
                    subprocess.run(f"taskkill /PID {pid} /F", shell=True, capture_output=True)
                    print(f"[Start] Killed PID {pid} on port {port}")
        else:
            subprocess.run(f"lsof -ti:{port} | xargs kill -9", shell=True)
    except Exception as e:
        print(f"[Start] Port cleanup warning: {e}")

if __name__ == "__main__":
    print("=" * 55)
    print("  RAKSHAK SEOC — Starting Backend")
    print("=" * 55)
    kill_port(PORT)

    # Set GEMINI_API_KEY if provided as environment variable
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print("[Warn] GEMINI_API_KEY not set. AI features will use fallback templates.")
        print("[Tip]  Run: set GEMINI_API_KEY=your_key_here && python start.py")

    # Launch Uvicorn
    os.execvp(sys.executable, [
        sys.executable, "-m", "uvicorn",
        "main:app",
        "--host", "0.0.0.0",
        "--port", str(PORT),
        "--log-level", "info",
    ])

