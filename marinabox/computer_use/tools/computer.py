import asyncio
import base64
import os
import shlex
import shutil
from enum import StrEnum
from pathlib import Path
from typing import Literal, TypedDict
from uuid import uuid4
import httpx

from anthropic.types.beta import BetaToolComputerUse20241022Param

from .base import BaseAnthropicTool, ToolError, ToolResult
from .run import run

OUTPUT_DIR = "/tmp/outputs"

TYPING_DELAY_MS = 12
TYPING_GROUP_SIZE = 50

Action = Literal[
    "key",
    "type",
    "mouse_move",
    "left_click",
    "left_click_drag",
    "right_click",
    "middle_click",
    "double_click",
    "screenshot",
    "cursor_position",
]


class Resolution(TypedDict):
    width: int
    height: int


# sizes above XGA/WXGA are not recommended (see README.md)
# scale down to one of these targets if ComputerTool._scaling_enabled is set
MAX_SCALING_TARGETS: dict[str, Resolution] = {
    "XGA": Resolution(width=1024, height=768),  # 4:3
    "WXGA": Resolution(width=1280, height=800),  # 16:10
    "FWXGA": Resolution(width=1366, height=768),  # ~16:9
}


class ScalingSource(StrEnum):
    COMPUTER = "computer"
    API = "api"


class ComputerToolOptions(TypedDict):
    display_height_px: int
    display_width_px: int
    display_number: int | None


def chunks(s: str, chunk_size: int) -> list[str]:
    return [s[i : i + chunk_size] for i in range(0, len(s), chunk_size)]


class ComputerTool(BaseAnthropicTool):
    """A tool that allows the agent to interact with the screen, keyboard, and mouse via API."""

    name: Literal["computer"] = "computer"
    api_type: Literal["computer_20241022"] = "computer_20241022"
    width: int = 1280
    height: int = 800
    
    def __init__(self, port: int = 8002):
        super().__init__()
        self.api_base_url = f"http://localhost:{port}"
        self.client = httpx.AsyncClient()

    @property
    def options(self) -> ComputerToolOptions:
        return {
            "display_width_px": self.width,
            "display_height_px": self.height,
            "display_number": None
        }

    def to_params(self) -> BetaToolComputerUse20241022Param:
        return {"name": self.name, "type": self.api_type, **self.options}

    async def __call__(
        self,
        *,
        action: Action,
        text: str | None = None,
        coordinate: tuple[int, int] | None = None,
        **kwargs,
    ):
        try:
            # Input validation
            if action in ("mouse_move", "left_click_drag"):
                if coordinate is None:
                    raise ToolError(f"coordinate is required for {action}")
                if text is not None:
                    raise ToolError(f"text is not accepted for {action}")
                if not isinstance(coordinate, (list, tuple)) or len(coordinate) != 2:
                    raise ToolError(f"{coordinate} must be a tuple of length 2")
                if not all(isinstance(i, int) and i >= 0 for i in coordinate):
                    raise ToolError(f"{coordinate} must be a tuple of non-negative ints")

            if action in ("key", "type"):
                if text is None:
                    raise ToolError(f"text is required for {action}")
                if coordinate is not None:
                    raise ToolError(f"coordinate is not accepted for {action}")
                if not isinstance(text, str):
                    raise ToolError(f"{text} must be a string")

            # API calls
            if action == "screenshot":
                response = await self.client.get(f"{self.api_base_url}/screenshot")
                response.raise_for_status()
                data = response.json()
                return ToolResult(base64_image=data["image"])

            params = {}
            if text:
                params["text"] = text
            if coordinate:
                params["coordinate"] = list(coordinate)  # Convert tuple to list for JSON

            response = await self.client.post(
                f"{self.api_base_url}/input/{action}", 
                json=params
            )
            response.raise_for_status()
            data = response.json()
            
            if action == "cursor_position":
                return ToolResult(output=f"X={data['x']},Y={data['y']}")
            
            return ToolResult(
                output=data.get("status"),
                base64_image=data.get("screenshot")
            )

        except httpx.HTTPError as e:
            return ToolResult(error=f"API request failed: {str(e)}")
