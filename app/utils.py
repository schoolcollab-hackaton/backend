
import os

def get_allowed_origins():
    origins = [
        "http://localhost:3000",
        "http://localhost:5000", 
        "http://localhost:5173",
    ]
    
    host = os.getenv("HOST", "127.0.0.1")
    print(f"Detected host: {host}")
    if host != "127.0.0.1":
        origins.extend([
            f"http://{host}:3000",
            f"http://{host}:5000", 
            f"http://{host}:5173",
        ])
    
    return origins