#!/bin/bash
# Log output to a specific file
LOG_FILE="/home/ec2-user/django-indexer/logs/deploy.log"

echo 'Running after_install.sh' >> "$LOG_FILE"

# Define the project directory
PROJECT_DIR="/home/ec2-user/django-indexer"

# Navigate to the project directory
cd "$PROJECT_DIR"

# Source the specific poetry virtual environment
source "/home/ec2-user/.cache/pypoetry/virtualenvs/django-indexer-Y-SQFfhb-py3.11/bin/activate"

# Check if there are pending migrations
if python manage.py showmigrations | grep '\[ \]'; then
    echo 'Migrations found, stopping services...' >> "$LOG_FILE"
    sudo systemctl stop gunicorn.service celery.service

    echo 'Applying migrations...' >> "$LOG_FILE"
    python manage.py migrate >> "$LOG_FILE"

    echo 'Starting services...' >> "$LOG_FILE"
    sudo systemctl start gunicorn.service celery.service
else
    echo 'No migrations found. Running collectstatic and restarting services...' >> "$LOG_FILE"
    python manage.py collectstatic --noinput >> "$LOG_FILE"
    sudo systemctl restart gunicorn.service celery.service
fi

echo 'after_install.sh completed' >> "$LOG_FILE"
