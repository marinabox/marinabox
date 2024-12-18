from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

@dataclass
class BrowserSession:
    session_id: str
    container_id: str
    vnc_port: int
    computer_use_port: int
    created_at: datetime
    env_type: str  # 'browser' or 'desktop'
    debug_port: Optional[int] = None  # Only needed for browser environment
    closed_at: Optional[datetime] = None
    runtime_seconds: Optional[float] = None
    websocket_url: Optional[str] = None
    status: str = "running"
    resolution: str = "1280x800x24"
    video_path: Optional[str] = None
    tag: Optional[str] = None
    
    # Add this to ensure the class can be pickled
    def __getstate__(self):
        return self.__dict__
    
    def __setstate__(self, state):
        self.__dict__.update(state)

    def get_current_runtime(self) -> float:
        """Calculate the current runtime in seconds"""
        if self.runtime_seconds is not None:
            return self.runtime_seconds
        return (datetime.now(timezone.utc) - self.created_at).total_seconds()

    def to_dict(self) -> dict:
        """Convert session to dictionary with current runtime"""
        data = self.__dict__.copy()
        if self.status == "running":
            data['runtime_seconds'] = self.get_current_runtime()
        return data