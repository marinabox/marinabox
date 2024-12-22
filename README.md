# Marinabox

A container management system for browser automation that provides both browser and desktop environments.

## Prerequisites

- Docker
- Python 3.7 or higher
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
# Clone the repository
git clone https://github.com/yourusername/marinabox
cd marinabox

# Install the package in development mode
pip install -e .
```

Alternatively, you can install directly from PyPI (if published):
```bash
pip install marinabox
```