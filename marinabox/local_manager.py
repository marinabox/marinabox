import docker
import requests
import time
import pickle
import os
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timezone

from .models import BrowserSession

class LocalContainerManager:
    def __init__(self, base_debug_port: int = 4002, base_vnc_port: int = 5002, base_computer_use_port: int = 8002, videos_path: Optional[Path] = None):
        self.client = docker.from_env()
        self.base_debug_port = base_debug_port
        self.base_vnc_port = base_vnc_port
        self.base_computer_use_port = base_computer_use_port
        self.sessions = {}
        self.closed_sessions = {}
        self.storage_path = Path.home() / ".marinabox" / "sessions.pkl"
        self.closed_storage_path = Path.home() / ".marinabox" / "closed_sessions.pkl"
        self.videos_path = videos_path or (Path.home() / ".marinabox" / "videos")
        self.videos_path.mkdir(parents=True, exist_ok=True)
        self.console_logs_path = Path("marinabox/data/console_logs")
        self.console_logs_path.mkdir(parents=True, exist_ok=True)
        self.input_queue_path = Path("marinabox/data/input_queue")
        self.input_queue_path.mkdir(parents=True, exist_ok=True)
        self._load_sessions()
        self._load_closed_sessions()

    def _ensure_storage_dir(self):
        """Ensure the storage directory exists"""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
    def _save_sessions(self):
        """Save sessions to disk"""
        self._ensure_storage_dir()
        with open(self.storage_path, 'wb') as f:
            pickle.dump(self.sessions, f)
            
    def _load_sessions(self):
        """Load sessions from disk and verify they still exist"""
        try:
            if self.storage_path.exists():
                with open(self.storage_path, 'rb') as f:
                    self.sessions = pickle.load(f)
                    
                # Verify containers still exist and remove stale sessions
                active_containers = {c.id for c in self.client.containers.list()}
                stale_sessions = [
                    session_id for session_id, session in self.sessions.items()
                    if session.container_id not in active_containers
                ]
                for session_id in stale_sessions:
                    del self.sessions[session_id]
                
                if stale_sessions:
                    self._save_sessions()
        except Exception as e:
            print(f"Error loading sessions: {e}")
            self.sessions = {}
    
    def _find_available_ports(self, env_type: str) -> tuple[Optional[int], int, int]:
        used_vnc_ports = {session.vnc_port for session in self.sessions.values()}
        used_computer_use_ports = {session.computer_use_port for session in self.sessions.values()}
        
        if env_type == 'browser':
            used_debug_ports = {session.debug_port for session in self.sessions.values() if session.debug_port is not None}
            debug_port = self.base_debug_port
            while debug_port in used_debug_ports:
                debug_port += 2
        else:
            debug_port = None
            
        vnc_port = self.base_vnc_port
        while vnc_port in used_vnc_ports:
            vnc_port += 2

        computer_use_port = self.base_computer_use_port
        while computer_use_port in used_computer_use_ports:
            computer_use_port += 2
            
        return debug_port, vnc_port, computer_use_port
    
    def create_session(self, env_type: str = "browser", resolution: str = "1280x800x24", tag: Optional[str] = None) -> BrowserSession:
        if env_type not in ["browser", "desktop"]:
            raise ValueError("env_type must be either 'browser' or 'desktop'")

        debug_port, vnc_port, computer_use_port = self._find_available_ports(env_type)
        
        # Configure ports based on environment type
        ports = {
            '6081/tcp': vnc_port,
            '8000/tcp': computer_use_port
        }
        if env_type == 'browser':
            ports['9222/tcp'] = debug_port
        
        # Select appropriate image
        image = "marinabox/marinabox-browser" if env_type == "browser" else "marinabox/marinabox-desktop"
        
        container = self.client.containers.run(
            image,
            detach=True,
            environment={"RESOLUTION": resolution},
            ports=ports
        )
        
        # Wait for container to be ready
        time.sleep(2)
        
        # Get WebSocket URL only for browser environment
        websocket_url = None
        if env_type == 'browser':
            try:
                response = requests.get(f"http://127.0.0.1:{debug_port}/json/version")
                websocket_url = response.json().get("webSocketDebuggerUrl")
            except:
                websocket_url = None
            
        session = BrowserSession(
            session_id=container.id[:12],
            container_id=container.id,
            debug_port=debug_port,
            vnc_port=vnc_port,
            computer_use_port=computer_use_port,
            created_at=datetime.now(timezone.utc),
            websocket_url=websocket_url,
            resolution=resolution,
            env_type=env_type,
            tag=tag
        )
        
        self.sessions[session.session_id] = session
        self._save_sessions()
        
        # Create empty console log file for the session
        console_log_file = self.console_logs_path / f"{session.session_id}.txt"
        console_log_file.touch()
        
        # Create empty input queue file for the session
        input_queue_file = self.input_queue_path / f"{session.session_id}.txt"
        input_queue_file.touch()
        
        return session
    
    def list_sessions(self) -> List[BrowserSession]:
        self._load_sessions()
        return list(self.sessions.values())
    
    def get_session(self, session_id: str) -> Optional[BrowserSession]:
        return self.sessions.get(session_id)
    
    def stop_session(self, session_id: str, video_filename: Optional[str] = None) -> bool:
        if session_id not in self.sessions:
            return False
            
        session = self.sessions[session_id]
        try:
            container = self.client.containers.get(session.container_id)
            
            # Gracefully stop ffmpeg first
            container.exec_run("/usr/bin/supervisorctl -c /etc/supervisor.d/supervisord.ini stop ffmpeg")
            time.sleep(2)
            
            # Use provided filename or default to session_id
            video_filename = video_filename or f"{session_id}.mp4"
            video_path = self.videos_path / video_filename
            
            # Create directory if it doesn't exist
            video_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy the video file from container before stopping
            import subprocess
            subprocess.run([
                "docker", "cp",
                f"{container.id}:/tmp/session.mp4",
                str(video_path)
            ])
            
            container.stop()
            container.remove()
            
            # Update session with closing details
            session.status = "stopped"
            session.closed_at = datetime.now(timezone.utc)
            session.runtime_seconds = (session.closed_at - session.created_at).total_seconds()
            session.video_path = str(video_path)
            
            # Move to closed sessions
            self.closed_sessions[session_id] = session
            del self.sessions[session_id]
            
            # Save both session lists
            self._save_sessions()
            self._save_closed_sessions()
            return True
        except Exception as e:
            print(f"Error stopping session: {e}")
            return False
    
    def _save_closed_sessions(self):
        """Save closed sessions to disk"""
        self._ensure_storage_dir()
        with open(self.closed_storage_path, 'wb') as f:
            pickle.dump(self.closed_sessions, f)
    
    def _load_closed_sessions(self):
        """Load closed sessions from disk"""
        try:
            if self.closed_storage_path.exists():
                with open(self.closed_storage_path, 'rb') as f:
                    self.closed_sessions = pickle.load(f)
        except Exception as e:
            print(f"Error loading closed sessions: {e}")
            self.closed_sessions = {}
    
    def list_closed_sessions(self) -> List[BrowserSession]:
        """Return list of closed sessions"""
        return list(self.closed_sessions.values())
    
    def get_closed_session(self, session_id: str) -> Optional[BrowserSession]:
        """Get details of a specific closed session"""
        return self.closed_sessions.get(session_id)
    
    def update_tag(self, session_id: str, tag: str) -> Optional[BrowserSession]:
        """Update the tag for a session"""
        session = self.get_session(session_id)
        if session:
            session.tag = tag
            self._save_sessions()
            return session
        
        # Check closed sessions
        session = self.get_closed_session(session_id)
        if session:
            session.tag = tag
            self._save_closed_sessions()
            return session
        
        return None

    def get_console_log_path(self, session_id: str) -> Path:
        """Get the path to a session's console log file"""
        return self.console_logs_path / f"{session_id}.txt"

    def write_to_console_log(self, session_id: str, message: str):
        """Write a message to the session's console log"""
        log_file = self.get_console_log_path(session_id)
        with open(log_file, 'a') as f:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"[{timestamp}] {message}\n")

    def write_to_input_queue(self, session_id: str, message: str) -> bool:
        """Write a message to the session's input queue"""
        try:
            session = self.get_session(session_id)
            if not session:
                return False
                
            input_file = self.input_queue_path / f"{session_id}.txt"
            with open(input_file, "a") as f:
                f.write(f"{message}\n")
            return True
        except Exception as e:
            print(f"Error writing to input queue: {e}")
            return False

    def get_input_queue_path(self, session_id: str) -> Path:
        """Get the path to a session's input queue file"""
        return self.input_queue_path / f"{session_id}.txt"