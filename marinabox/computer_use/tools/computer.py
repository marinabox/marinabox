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

from anthropic.types.beta import BetaToolComputerUse20250124Param

from .base import BaseAnthropicTool, ToolError, ToolResult
from .run import run

OUTPUT_DIR = "/tmp/outputs"

TYPING_DELAY_MS = 12
TYPING_GROUP_SIZE = 50

# Scroll behavior tuning
SCROLL_STEP_DELAY_S: float = 0.10
SCROLL_BATCH_SIZE: int = 8
SCROLL_BATCH_PAUSE_S: float = 0.25


def _http_error_detail(e: Exception) -> str:
    if isinstance(e, httpx.HTTPStatusError) and e.response is not None:
        try:
            body = e.response.text
        except Exception:
            body = "<no body>"
        req = e.request
        return f"{e.response.status_code} {e.response.reason_phrase} {req.method} {req.url} body={body}"
    if isinstance(e, httpx.TimeoutException):
        req = getattr(e, "request", None)
        return f"timeout {getattr(req, 'method', '')} {getattr(req, 'url', '')}"
    return repr(e)

Action = Literal[
    "key",
    "type",
    "mouse_move",
    "left_click",
    "left_click_drag",
    "right_click",
    "middle_click",
    "double_click",
    "scroll",
    "screenshot",
    "cursor_position",
    "wait",
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
    api_type: Literal["computer_20250124"] = "computer_20250124"
    width: int = 1280
    height: int = 800
    
    def __init__(self, port: int = 8002):
        super().__init__()
        self.api_base_url = f"http://localhost:{port}"
        # Increase default timeout to handle slower actions from the tool server
        self.request_timeout_s: float = 30.0
        self.client = httpx.AsyncClient(timeout=self.request_timeout_s)

    @property
    def options(self) -> ComputerToolOptions:
        return {
            "display_width_px": self.width,
            "display_height_px": self.height,
            "display_number": None
        }

    def to_params(self) -> BetaToolComputerUse20250124Param:
        return {"name": self.name, "type": self.api_type, **self.options}

    async def _post(self, path: str, json: dict, timeout: float | None = None, retries: int = 2) -> httpx.Response:
        last_exc: Exception | None = None
        url = f"{self.api_base_url}{path}"
        for attempt in range(retries + 1):
            try:
                resp = await self.client.post(url, json=json, timeout=timeout or self.request_timeout_s)
                resp.raise_for_status()
                return resp
            except httpx.HTTPError as e:
                last_exc = e
                if attempt < retries:
                    await asyncio.sleep(0.3 * (2 ** attempt))
                    continue
                raise

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
            if action == "scroll":
                scroll_direction = kwargs.get("scroll_direction", "down")
                scroll_amount = kwargs.get("scroll_amount", 10)
                if scroll_direction not in ("down", "up"):
                    raise ToolError("scroll_direction must be 'down' or 'up'")
                if not isinstance(scroll_amount, int) or scroll_amount <= 0:
                    raise ToolError("scroll_amount must be a positive integer")

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
            if action == "wait":
                duration = kwargs.get("duration", 1)
                if not isinstance(duration, (int, float)) or duration < 0:
                    raise ToolError("duration must be a non-negative number for wait")
                await asyncio.sleep(duration)
                return ToolResult(output=f"waited {duration} seconds")
            if action == "screenshot":
                response = await self.client.get(
                    f"{self.api_base_url}/screenshot",
                    timeout=self.request_timeout_s,
                )
                response.raise_for_status()
                data = response.json()
                return ToolResult(base64_image=data["image"])

            # Handle scroll by translating into key presses to improve compatibility
            if action == "scroll":
                # Optionally move the mouse to the target area before scrolling (disabled by default)
                move_pointer: bool = bool(kwargs.get("move_pointer", False))
                if move_pointer and coordinate is not None:
                    # Best-effort: do not fail the scroll if mouse_move times out
                    try:
                        await self._post("/input/mouse_move", {"coordinate": list(coordinate)})
                        await asyncio.sleep(0.05)
                    except httpx.HTTPError:
                        pass

                direction = kwargs.get("scroll_direction", "down")
                granularity = kwargs.get("granularity", "page")  # "line" or "page"
                # Re-enable click-based focusing by default; target the scrollbar gutter by default
                click_to_focus: bool = bool(kwargs.get("click_to_focus", True))
                focus_target: str = str(kwargs.get("focus_target", "gutter"))  # "gutter" | "coordinate"
                jump_to_boundary: bool = bool(kwargs.get("jump_to_boundary", False))
                # Build a safe, clickless key strategy that avoids jumping to the absolute end by default
                if direction == "down":
                    # prefer page-based movement; fall back progressively (no End by default)
                    key_strategy = ["PageDown", "Space", "ArrowDown"] if granularity == "page" else ["ArrowDown", "PageDown", "Space"]
                else:  # up (no Home by default)
                    key_strategy = ["PageUp", "ArrowUp"] if granularity == "page" else ["ArrowUp", "PageUp"]
                steps: int = kwargs.get("scroll_amount", 10)
                if not isinstance(steps, int) or steps <= 0:
                    raise ToolError("scroll_amount must be a positive integer")

                last_data = None
                # optionally click to focus the intended container
                if click_to_focus and focus_target == "coordinate" and coordinate is not None:
                    try:
                        await self._post("/input/mouse_move", {"coordinate": list(coordinate)})
                        await asyncio.sleep(0.05)
                        await self._post("/input/left_click", {"coordinate": list(coordinate)})
                        await asyncio.sleep(0.05)
                    except httpx.HTTPError:
                        pass

                # optionally click the scrollbar gutter to focus page-level scroll (default)
                if click_to_focus and focus_target == "gutter":
                    try:
                        gutter_coord = [max(self.width - 5, 0), max(self.height - 5, 0)]
                        await self._post("/input/mouse_move", {"coordinate": gutter_coord})
                        await asyncio.sleep(0.05)
                        await self._post("/input/left_click", {"coordinate": gutter_coord})
                        await asyncio.sleep(0.05)
                    except httpx.HTTPError:
                        pass

                # Optional key-only pre-focus routine to avoid clicks
                focus_strategy: str = str(kwargs.get("focus_strategy", "escape_tab"))  # none|escape|tab|escape_tab
                focus_tab_count: int = int(kwargs.get("focus_tab_count", 4))
                if focus_strategy in ("escape", "escape_tab"):
                    try:
                        await self._post("/input/key", {"text": "Escape"}, timeout=10.0)
                        await asyncio.sleep(0.05)
                    except httpx.HTTPError:
                        pass
                if focus_strategy in ("tab", "escape_tab") and focus_tab_count > 0:
                    for _ in range(min(max(focus_tab_count, 0), 10)):
                        try:
                            await self._post("/input/key", {"text": "Tab"}, timeout=10.0)
                            await asyncio.sleep(0.05)
                        except httpx.HTTPError:
                            break

                # Optionally jump directly to boundary if explicitly requested
                if jump_to_boundary:
                    try:
                        boundary_key = "End" if direction == "down" else "Home"
                        resp = await self._post("/input/key", {"text": boundary_key}, timeout=15.0)
                        last_data = resp.json()
                        # After a boundary jump, no further steps are necessary
                        return ToolResult(
                            output=last_data.get("status"),
                            base64_image=last_data.get("screenshot")
                        )
                    except httpx.HTTPError:
                        # If boundary key fails, continue with regular strategy
                        pass

                for i in range(steps):
                    sent = False
                    last_exc: Exception | None = None
                    for key in key_strategy:
                        try:
                            resp = await self._post("/input/key", {"text": key}, timeout=15.0)
                            last_data = resp.json()
                            sent = True
                            break
                        except httpx.HTTPError as e:
                            last_exc = e
                            continue
                    if not sent:
                        return ToolResult(error=f"scroll failed: {_http_error_detail(last_exc) if last_exc else 'no key accepted'}")

                    await asyncio.sleep(SCROLL_STEP_DELAY_S)
                    if (i + 1) % SCROLL_BATCH_SIZE == 0:
                        await asyncio.sleep(SCROLL_BATCH_PAUSE_S)

                if last_data is None:
                    return ToolResult(error="scroll action produced no response")

                return ToolResult(
                    output=last_data.get("status"),
                    base64_image=last_data.get("screenshot")
                )

            params = {}
            if text:
                params["text"] = text
            if coordinate:
                params["coordinate"] = list(coordinate)  # Convert tuple to list for JSON

            # Improve reliability: move first, then click for pointer actions
            if action in ("left_click", "right_click", "double_click") and coordinate is not None:
                await self._post("/input/mouse_move", {"coordinate": list(coordinate)})
                await asyncio.sleep(0.05)

            response = await self._post(f"/input/{action}", params)
            response.raise_for_status()
            data = response.json()
            
            if action == "cursor_position":
                return ToolResult(output=f"X={data['x']},Y={data['y']}")
            
            return ToolResult(
                output=data.get("status"),
                base64_image=data.get("screenshot")
            )

        except httpx.HTTPError as e:
            return ToolResult(error=f"API request failed: {_http_error_detail(e)}")
