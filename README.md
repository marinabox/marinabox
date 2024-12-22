# Marinabox

Containerized sandboxes for AI agents

## Prerequisites

- Docker
- Python 3.12 or higher
- pip (Python package installer)

## Installation

1. First, ensure you have Docker installed on your system. If not, [install Docker](https://docs.docker.com/get-docker/) for your operating system.

2. Pull the required Docker images:
```bash
docker pull marinabox/marinabox-browser:latest
docker pull marinabox/marinabox-desktop:latest
```

3. Install the Marinabox package:
```bash
pip install marinabox
```

## Usage Example

Here's a basic example of how to use the Marinabox SDK:

```python
from marinabox import MarinaboxSDK

# Initialize the SDK
mb = MarinaboxSDK()

# Set Anthropic API key
mb.set_anthropic_key(ANTHROPIC_API_KEY)

# Create a new session
session = mb.create_session(env_type="browser", tag="my-session")
print(f"Created session: {session.session_id}")

# List active sessions
sessions = mb.list_sessions()
for s in sessions:
    print(f"Active session: {s.session_id} (Tag: {s.tag})")

# Execute a computer use command
mb.computer_use_command("my-session", "Navigate to https://x.ai")
