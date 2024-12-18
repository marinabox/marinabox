from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from fastapi.responses import FileResponse, StreamingResponse
from pathlib import Path
import os
from datetime import datetime

from marinabox.local_manager import LocalContainerManager
from marinabox.models import BrowserSession
import uvicorn
from .config import Config
from .computer_use.cli import main as computer_use_main

app = FastAPI(title="Marinabox API", root_path="/api")

# Add CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# manager = LocalContainerManager()

@app.post("/sessions", response_model=BrowserSession)
async def create_session(env_type: str = "browser", resolution: str = "1280x800x24", tag: Optional[str] = None):
    """Create a new session with specified environment type"""
    manager = LocalContainerManager()
    return manager.create_session(env_type=env_type, resolution=resolution, tag=tag)

@app.get("/sessions", response_model=List[BrowserSession])
async def list_sessions():
    """List all active sessions"""
    manager = LocalContainerManager()
    sessions = manager.list_sessions()
    # Update runtime_seconds for each active session
    for i, session in enumerate(sessions):
        if session.status == "running":
            sessions[i] = session.to_dict()

    print(sessions)
    return sessions

@app.get("/sessions/closed", response_model=List[BrowserSession])
async def list_closed_sessions():
    """List all closed sessions"""
    manager = LocalContainerManager()
    return manager.list_closed_sessions()

@app.get("/sessions/{session_id}", response_model=BrowserSession)
async def get_session(session_id: str):
    """Get details for a specific session"""
    manager = LocalContainerManager()
    session = manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status == "running":
        session.runtime_seconds = session.get_current_runtime()
    return session

@app.delete("/sessions/{session_id}")
async def stop_session(session_id: str):
    """Stop a browser session"""
    manager = LocalContainerManager()
    success = manager.stop_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "success"}

@app.get("/sessions/closed/{session_id}", response_model=BrowserSession)
async def get_closed_session(session_id: str):
    """Get details for a specific closed session"""
    manager = LocalContainerManager()
    session = manager.get_closed_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Closed session not found")
    return session

@app.get("/videos/{session_id}")
async def get_session_video(session_id: str):
    """Get the video recording for a session"""
    manager = LocalContainerManager()
    video_path = manager.videos_path / f"{session_id}.mp4"
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video not found")

    def iterfile():
        with open(video_path, "rb") as file:
            yield from file

    # Get file size for Content-Length header
    file_size = os.path.getsize(video_path)

    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(file_size),
        "Content-Type": "video/mp4",
        "Cache-Control": "public, max-age=3600"
    }

    return StreamingResponse(
        iterfile(),
        headers=headers,
        media_type="video/mp4"
    )

@app.put("/sessions/{session_id}/tag")
async def update_session_tag(session_id: str, tag: str):
    """Update tag for a session"""
    manager = LocalContainerManager()
    session = manager.update_tag(session_id, tag)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@app.post("/sessions/{session_id}/computer-use")
async def execute_computer_use(session_id: str, command: str):
    """Execute computer use command on a session"""
    config = Config()
    api_key = config.get_anthropic_key()
    if not api_key:
        raise HTTPException(status_code=400, detail="Anthropic API key not configured")

    manager = LocalContainerManager()
    session = manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        await computer_use_main(command, api_key, session.computer_use_port)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    
    uvicorn.run(app, host="0.0.0.0", port=8000)