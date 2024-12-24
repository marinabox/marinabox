<div align="center">
  <img src="frontend/public/logo.svg" alt="MarinaBox Logo" width="100" height="100" />
  <h1>MarinaBox</h1>
  
  <p>
    <img alt="GitHub Repo stars" src="https://img.shields.io/github/stars/marinabox/marinabox?style=flat-square&logo=github">
    <img alt="GitHub forks" src="https://img.shields.io/github/forks/marinabox/marinabox?style=flat-square&logo=github">
    <img alt="GitHub issues" src="https://img.shields.io/github/issues/marinabox/marinabox?style=flat-square&logo=github">
    <img alt="GitHub license" src="https://img.shields.io/github/license/marinabox/marinabox?style=flat-square&logo=github">
  </p>
</div>

MarinaBox is a toolkit for creating and managing secure, isolated environments for AI agents. It provides:

### Core Features

1. **Secure Sandboxed Environments**
   - Run isolated browser and desktop sessions locally or cloud
   - Perfect for AI agent tasks(Computer Use) and browser automation

2. **Comprehensive SDK & CLI**
   - Python SDK for programmatic control
   - Command-line interface for session management
   - Real-time monitoring and control capabilities
   - Integration with popular automation tools (Playwright, Selenium)

3. **Interactive UI Dashboard**
   - Live session viewing and control
   - Session recording and playback
   - Session management interface

### Additional Features

- **Cloud Integration**: Deploy sandboxes to major cloud providers(coming soon)
- **Multi-session Management**: Run multiple isolated environments simultaneously
- **Session Tagging**: Organize and track sessions with custom tags

## Documentation

Full documentation is available at [https://marinabox.mintlify.app/get-started/introduction](https://marinabox.mintlify.app/get-started/introduction)

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

## Important Note

The provided Docker images are built for Mac ARM64 architecture (Apple Silicon). For other architectures:

1. Clone the sandbox repository:
```bash
git clone https://github.com/marinabox/marinabox-sandbox
```

2. Build the images with your target platform:
```bash
docker build --platform <your-platform> -f Dockerfile.chromium -t marinabox/marinabox-browser .
docker build --platform <your-platform> -f Dockerfile.desktop -t marinabox/marinabox-desktop .
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

```

## License

MarinaBox is released under the MIT License. See the [LICENSE](LICENSE) file for details.

## Acknowledgments

This project makes significant use of:
- [noVNC](https://github.com/novnc/noVNC), an open source VNC client using HTML5 (WebSockets, Canvas). noVNC is licensed under the MPL-2.0 License.
- [Anthropic Quickstarts](https://github.com/anthropics/anthropic-quickstarts), specifically the Computer Use Demo which provided inspiration for the sandbox implementation. Licensed under the MIT License.
