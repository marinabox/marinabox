from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from fastapi.responses import FileResponse, StreamingResponse
from pathlib import Path
import os
from datetime import datetime
import threading

# Add these imports to your existing imports
from fastapi.responses import StreamingResponse
import asyncio
import aiofiles

from marinabox.local_manager import LocalContainerManager
from marinabox.models import BrowserSession
import uvicorn
from .config import Config
from .computer_use.cli import main as computer_use_main
from samthropic import setup_output_directories, samthropic_agent, mb

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

# Store running samthropic processes
samthropic_processes = {}

def run_samthropic_session(session_id: str):
    """Run the samthropic agent for a session"""
    try:
        # Set up logging
        log_console = f"marinabox/data/console_logs/{session_id}.txt"
        Path(log_console).parent.mkdir(parents=True, exist_ok=True)
        
        with open(log_console, 'w') as f_session:
            # Redirect stdout to file
            import sys
            original_stdout = sys.stdout
            sys.stdout = f_session

            # Initialize the agent state
            samthropic_agent.invoke({
                "input_task": "", 
                "conversation_history": [], 
                "sams_thought": "", 
                "screen_description": "", 
                "steps_taken_by_computer_guy": "",
                "session_id": session_id
            }, {"recursion_limit": 500})

            # Restore stdout
            sys.stdout = original_stdout

    except Exception as e:
        print(f"Error in samthropic session: {e}")

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

@app.get("/console/{session_id}")
async def get_console_output(session_id: str):
    # Ensure the path exists
    output_file = Path("marinabox/data/console_logs") / f"{session_id}.txt"
    print(f"Attempting to read log file: {output_file}")
    
    try:
        if not output_file.exists():
            print(f"Log file not found: {output_file}")
            return {"output": []}
            
        with open(output_file, "r") as f:
            lines = f.readlines()
            print(f"Read {len(lines)} lines from log file")
            
        return {"output": lines}
        
    except Exception as e:
        print(f"Error reading console output: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
# Add this new endpoint
@app.get("/console/stream/{session_id}")
async def stream_console_output(session_id: str):
    output_file = Path(f"marinabox/data/console_logs/{session_id}.txt")
    
    if not output_file.exists():
        raise HTTPException(status_code=404, detail="Console log file not found")
    
    async def log_generator():
        async with aiofiles.open(output_file, mode='r') as file:
            # First, read existing content
            content = await file.read()
            for line in content.splitlines():
                print(line)
                yield f"data: {line}\n\n"
            
            # Seek to end of file
            await file.seek(0, 2)
            
            while True:
                line = await file.readline()
                if line:
                    yield f"data: {line.strip()}\n\n"
                else:
                    await asyncio.sleep(0.1)  # Small delay before next check
    
    return StreamingResponse(
        log_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

@app.post("/sessions/{session_id}/chat")
async def send_chat_message(session_id: str, message: str = Query(...)):
    """Send a chat message to a running session"""
    try:
        # Create directory if it doesn't exist
        Path("marinabox/data/input_queue").mkdir(parents=True, exist_ok=True)
        
        # Write the message to the session's input queue
        input_file = Path(f"marinabox/data/input_queue/{session_id}.txt")
        
        with open(input_file, "a") as f:
            f.write(f"{message}\n")
        
        return {"status": "success", "message": message}
    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/sessions/{session_id}/start-samthropic")
async def start_samthropic(session_id: str):
    """Start a samthropic session"""
    try:
        manager = LocalContainerManager()
        session = manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        setup_output_directories()
        
        # Start samthropic in a separate thread
        thread = threading.Thread(
            target=run_samthropic_session,
            args=(session_id,)
        )
        thread.daemon = True  # Make thread daemon so it exits when main process exits
        thread.start()
        samthropic_processes[session_id] = thread
        
        return {"status": "success"}
    except Exception as e:
        print(f"Error starting samthropic: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    
    uvicorn.run(app, host="0.0.0.0", port=8000)