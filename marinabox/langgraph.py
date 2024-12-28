from .local_manager import LocalContainerManager
from langgraph.types import Command
from .sdk import MarinaboxSDK
from langchain_core.tools import BaseTool
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState, InjectedStore
from langchain_core.tools.base import InjectedToolCallId
from typing import Annotated
from langchain_core.messages import HumanMessage, ToolMessage

def mb_start_computer(state: Annotated[dict, InjectedState()]):
    manager = LocalContainerManager()
    env_type = "desktop"
    resolution = "1280x800x24"
    session_details = manager.create_session(env_type=env_type, resolution=resolution)
    state["session_details"] = session_details
    state["session_id"] = session_details.session_id
    return state

def mb_stop_computer(state: Annotated[dict, InjectedState()]):
    manager = LocalContainerManager()
    session_id = state.get("session_id")

    manager.stop_session(session_id)
    
    state["session_details"] = None
    return state

def mb_start_browser(state: Annotated[dict, InjectedState()]):
    manager = LocalContainerManager()
    env_type = "browser"
    resolution = "1280x800x24"
    session_details = manager.create_session(env_type=env_type, resolution=resolution)
    state["session_details"] = session_details
    state["session_id"] = session_details.session_id
    return state

def mb_stop_browser(state: Annotated[dict, InjectedState()]):
    manager = LocalContainerManager()
    session_id = state.get("session_id")
    
    manager.stop_session(session_id)
    
    state["session_details"] = None
    return state

@tool  
def mb_use_computer_tool(tool_call_id: Annotated[str, InjectedToolCallId],state: Annotated[dict, InjectedState()], command: str, next_node: str):
    """A tool used to execute commands on a computer using Natural Language"""
    mb_sdk = MarinaboxSDK()
    session_id = state.get("session_id")
    mb_sdk.computer_use_command(state.get("session_id"), command)
    
    return Command(goto="agent")

@tool  
def mb_use_browser_tool(tool_call_id: Annotated[str, InjectedToolCallId], state: Annotated[dict, InjectedState()], command: str, next_node: str):
    """A tool used to execute commands in a browser using Natural Language"""
    session_id = state.get("session_id")
    mb_sdk = MarinaboxSDK()
    session_id = state.get("session_id")
    mb_sdk.computer_use_command(state.get("session_id"), command)
    
    return Command(goto="agent")
