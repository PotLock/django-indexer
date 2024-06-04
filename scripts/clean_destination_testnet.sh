#!/bin/bash
# Directory to clean
DEST_DIR="/home/ec2-user/django-indexer-testnet"

# Delete all contents of the destination directory
if [ -d "$DEST_DIR" ]; then
    rm -rf "${DEST_DIR:?}/*"
fi