import click
from .local_manager import LocalContainerManager
import json
from datetime import datetime
from .config import Config
import asyncio
from .computer_use.cli import main as computer_use_main

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

@click.group()
def local():
    """Local container management commands"""
    pass

@local.command()
@click.option('--env-type', type=click.Choice(['browser', 'desktop']), default="browser", help='Environment type')
@click.option('--resolution', default="1280x800x24", help='Screen resolution')
@click.option('--tag', help='Add a tag to the session')
def create(env_type, resolution, tag):
    """Create a new session"""
    manager = LocalContainerManager()
    session = manager.create_session(env_type=env_type, resolution=resolution, tag=tag)
    click.echo(json.dumps(session.__dict__, cls=DateTimeEncoder, indent=2))

@local.command()
def list():
    """List all active sessions"""
    manager = LocalContainerManager()
    sessions = manager.list_sessions()
    click.echo(json.dumps([s.to_dict() for s in sessions], cls=DateTimeEncoder, indent=2))

@local.command()
@click.argument('session_id')
def get(session_id):
    """Get details for a specific session"""
    manager = LocalContainerManager()
    session = manager.get_session(session_id)
    if session:
        click.echo(json.dumps(session.to_dict(), cls=DateTimeEncoder, indent=2))
    else:
        click.echo("Session not found", err=True)

@local.command()
@click.argument('session_id')
def stop(session_id):
    """Stop a browser session"""
    manager = LocalContainerManager()
    success = manager.stop_session(session_id)
    if success:
        click.echo("Session stopped successfully")
    else:
        click.echo("Failed to stop session", err=True)

@local.command()
def list_closed():
    """List all closed sessions"""
    manager = LocalContainerManager()
    sessions = manager.list_closed_sessions()
    click.echo(json.dumps([s.__dict__ for s in sessions], cls=DateTimeEncoder, indent=2))

@local.command()
@click.argument('session_id')
def get_closed(session_id):
    """Get details for a specific closed session"""
    manager = LocalContainerManager()
    session = manager.get_closed_session(session_id)
    if session:
        data = session.__dict__.copy()
        if session.video_path:
            data['video_path'] = str(session.video_path)
        click.echo(json.dumps(data, cls=DateTimeEncoder, indent=2))
    else:
        click.echo("Closed session not found", err=True)

@local.command()
@click.argument('session_id')
@click.argument('tag')
def tag(session_id, tag):
    """Add or update tag for a session"""
    manager = LocalContainerManager()
    session = manager.update_tag(session_id, tag)
    if session:
        click.echo(json.dumps(session.__dict__, cls=DateTimeEncoder, indent=2))
    else:
        click.echo("Session not found", err=True)

@local.command()
@click.option('--anthropic-api-key', required=True, help='Anthropic API key')
def set(anthropic_api_key):
    """Set configuration values"""
    config = Config()
    config.set_anthropic_key(anthropic_api_key)
    click.echo("API key set successfully")

@local.command()
@click.argument('session_identifier')
@click.option('--command', required=True, help='Command to execute')
def computer_use(session_identifier, command):
    """Execute computer use command on a session"""
    # Check for API key
    config = Config()
    api_key = config.get_anthropic_key()
    if not api_key:
        click.echo("Error: Anthropic API key not set. Use 'mb local set --anthropic-api-key' first", err=True)
        return

    # Get session by ID or tag
    manager = LocalContainerManager()
    session = None
    
    # Try by ID first
    session = manager.get_session(session_identifier)
    
    # If not found, try by tag
    if not session:
        sessions = manager.list_sessions()
        matching_sessions = [s for s in sessions if s.tag == session_identifier]
        if len(matching_sessions) == 1:
            session = matching_sessions[0]
        elif len(matching_sessions) > 1:
            click.echo("Error: Multiple sessions found with this tag", err=True)
            return
    
    if not session:
        click.echo("Error: No session found with this ID or tag", err=True)
        return

    
    # Execute computer use command
    asyncio.run(computer_use_main(command, api_key, session.computer_use_port)) 