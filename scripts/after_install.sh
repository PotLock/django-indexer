#!/bin/bash
# Log output to a specific file
LOG_FILE="/home/ec2-user/django-indexer/logs/deploy.log"

echo 'Running after_install.sh' >> "$LOG_FILE"

# Log the current date and time in a human-readable format
echo "Script execution started at: $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG_FILE"

# Define the project directory
PROJECT_DIR="/home/ec2-user/django-indexer"

# Navigate to the project directory
cd "$PROJECT_DIR"

# Source the specific poetry virtual environment
source "/home/ec2-user/.cache/pypoetry/virtualenvs/django-indexer-Y-SQFfhb-py3.11/bin/activate"

# Check if there are pending migrations
if python manage.py showmigrations | grep '\[ \]'; then
    echo 'Migrations found; stopping services...' >> "$LOG_FILE"
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

# Set correct ownership recursively for all files and directories in the project directory
sudo chown -R ec2-user:ec2-user /home/ec2-user/django-indexer/
echo "$(date) - Changed ownership to ec2-user for all project files" >> "$LOG_FILE"

# Set read, write, and execute permissions for the owner and group, and read and execute for others
sudo chmod -R 775 /home/ec2-user/django-indexer/
echo "$(date) - Set permissions to 775 for all project files" >> "$LOG_FILE"

# Set the group of the Django project and static files to nginx
sudo chown -R ec2-user:nginx /home/ec2-user/django-indexer

# Set the group of the socket directory to nginx
sudo chown -R ec2-user:nginx /home/ec2-user/django-indexer/run

# # Log the results of permissions change
# echo "Permissions after update:" >> "$LOG_FILE"
# ls -lah /home/ec2-user/django-indexer/ >> "$LOG_FILE"

echo 'after_install.sh completed' >> "$LOG_FILE"
