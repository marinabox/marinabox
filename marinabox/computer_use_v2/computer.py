from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Optional, Tuple, Any, Dict

import requests

from ..sdk import MarinaboxSDK


@dataclass
class ComputerConfig:
    """Configuration for connecting to a Marinabox computer-use v2 API."""
    base_url: str
    request_timeout_s: float = 30.0


class Computer:
    """
    High-level client for the v2 Computer Use API (mouse/keyboard/screenshot).
    
    Instantiate with either:
    - session_identifier: an active Marinabox session ID or tag
    - base_url: explicit API base URL (e.g., http://localhost:2000)
    
    If both are provided, base_url takes precedence.
    """

    def __init__(
        self,
        *,
        session_identifier: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout_s: float = 30.0,
    ) -> None:
        if base_url:
            resolved_url = base_url.rstrip("/")
        elif session_identifier:
            sdk = MarinaboxSDK()
            session = sdk.get_session_by_identifier(session_identifier)
            if not session:
                raise ValueError(f"No session found for identifier: {session_identifier}")
            # v2 API is exposed from the container on the computer_use_port
            resolved_url = f"http://localhost:{session.computer_use_port}"
        else:
            # Fallback for manual sandboxes
            resolved_url = "http://localhost:2000"

        self._config = ComputerConfig(base_url=resolved_url, request_timeout_s=timeout_s)
        self._http = requests.Session()

    # ----------------------------
    # Internal HTTP helpers
    # ----------------------------
    def _get(self, path: str) -> Dict[str, Any]:
        url = f"{self._config.base_url}{path}"
        resp = self._http.get(url, timeout=self._config.request_timeout_s)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self._config.base_url}{path}"
        resp = self._http.post(url, json=payload, timeout=self._config.request_timeout_s)
        resp.raise_for_status()
        return resp.json()

    # ----------------------------
    # Public API methods (v2)
    # ----------------------------
    @property
    def base_url(self) -> str:
        return self._config.base_url

    def screenshot_base64(self) -> str:
        """Return a base64-encoded PNG screenshot."""
        data = self._get("/screenshot")
        return str(data["image"])

    def screenshot(self) -> bytes:
        """Return raw PNG bytes of the current screen."""
        encoded = self.screenshot_base64()
        return base64.b64decode(encoded)

    def mouse_position(self) -> Tuple[int, int]:
        """Return (x, y) of the current mouse position."""
        data = self._get("/mouse_position")
        return int(data["x"]), int(data["y"])

    def mouse_move(self, x: int, y: int) -> Tuple[int, int]:
        """Move mouse to (x, y). Returns the target coordinates."""
        data = self._post("/mouse_move", {"x": int(x), "y": int(y)})
        return int(data.get("x", x)), int(data.get("y", y))

    def left_click(self, x: int, y: int) -> bool:
        """Move to (x, y) and left click."""
        data = self._post("/left_click", {"x": int(x), "y": int(y)})
        return str(data.get("status", "")).lower() == "success"

    def right_click(self, x: int, y: int) -> bool:
        """Move to (x, y) and right click."""
        data = self._post("/right_click", {"x": int(x), "y": int(y)})
        return str(data.get("status", "")).lower() == "success"

    def middle_click(self, x: int, y: int) -> bool:
        """Move to (x, y) and middle click."""
        data = self._post("/middle_click", {"x": int(x), "y": int(y)})
        return str(data.get("status", "")).lower() == "success"

    def double_click(self, x: int, y: int) -> bool:
        """Move to (x, y) and double click."""
        data = self._post("/double_click", {"x": int(x), "y": int(y)})
        return str(data.get("status", "")).lower() == "success"

    def key(self, text: str) -> bool:
        """
        Send a key press, e.g., 'Return', 'Escape', 'ctrl+c', or 'Alt+Tab'.
        The accepted strings must be compatible with xdotool's 'key' syntax.
        """
        if not text:
            raise ValueError("text is required for key()")
        data = self._post("/key", {"text": text})
        return str(data.get("status", "")).lower() == "success"

    def type_text(self, text: str) -> bool:
        """Type a string with natural delays."""
        if not text:
            raise ValueError("text is required for type_text()")
        data = self._post("/type", {"text": text})
        return str(data.get("status", "")).lower() == "success"

    # ----------------------------
    # Convenience constructors
    # ----------------------------
    @classmethod
    def from_session(cls, session_identifier: str, *, timeout_s: float = 30.0) -> "Computer":
        """Create a Computer bound to a running session by ID or tag."""
        return cls(session_identifier=session_identifier, timeout_s=timeout_s, sdk=sdk)

    @classmethod
    def from_url(cls, base_url: str, *, timeout_s: float = 30.0) -> "Computer":
        """Create a Computer bound to an explicit API base URL."""
        return cls(base_url=base_url, timeout_s=timeout_s)


