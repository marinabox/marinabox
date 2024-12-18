#!/bin/bash

# Build the image
docker build -t mb-manager .

# Run the container
docker run -d \
    --name mb-manager \
    -p 8000:8000 \
    -v ~/.marinabox:/root/.marinabox \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -e MARINABOX_DATA_DIR=/root/.marinabox \
    --restart unless-stopped \
    mb-manager