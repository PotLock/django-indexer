#!/bin/bash
# Log output to a specific file
LOG_FILE="/home/ec2-user/django-indexer-dev/logs/deploy.log"

echo -e "\n\n" >> "$LOG_FILE"
echo "=========================================" >> "$LOG_FILE"
echo "Running after_install_dev.sh at $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG_FILE"
echo "=========================================" >> "$LOG_FILE"

# Load env vars
export PL_ENVIRONMENT=dev
source /home/ec2-user/.bashrc

echo "PL_ENVIRONMENT: $PL_ENVIRONMENT" >> "$LOG_FILE"
echo "PL_POSTGRES_HOST: $PL_POSTGRES_HOST" >> "$LOG_FILE"

echo "PL_ENVIRONMENT: $PL_ENVIRONMENT" >> "$LOG_FILE"
echo "PL_POSTGRES_HOST: $PL_POSTGRES_HOST" >> "$LOG_FILE"

# Set correct ownership recursively for project directory
sudo chown -R ec2-user:nginx /home/ec2-user/django-indexer-dev/
echo "$(date '+%Y-%m-%d %H:%M:%S') - Corrected ownership to ec2-user:nginx" >> "$LOG_FILE"

# Set the necessary permissions
sudo chmod -R 775 /home/ec2-user/django-indexer-dev/
echo "$(date '+%Y-%m-%d %H:%M:%S') - Set permissions to 775" >> "$LOG_FILE"

# Restart nginx to apply any configuration changes
sudo systemctl restart nginx
echo "$(date '+%Y-%m-%d %H:%M:%S') - Restarted nginx" >> "$LOG_FILE"

# Define the project directory
PROJECT_DIR="/home/ec2-user/django-indexer-dev"

# Navigate to the project directory
cd "$PROJECT_DIR"

# Source the specific poetry virtual environment
source "/home/ec2-user/.cache/pypoetry/virtualenvs/django-indexer-Y-SQFfhb-py3.11/bin/activate"

# Install dependencies using Poetry
echo "$(date '+%Y-%m-%d %H:%M:%S') - Installing dependencies with Poetry" >> "$LOG_FILE"
poetry install >> "$LOG_FILE"
echo "$(date '+%Y-%m-%d %H:%M:%S') - Dependencies installed" >> "$LOG_FILE"

# Check if there are pending migrations and log the output
echo "Checking for pending migrations..." >> "$LOG_FILE"
PENDING_MIGRATIONS=$(poetry run python manage.py showmigrations | grep '\[ \]' 2>&1)  # Redirect stderr to stdout
echo "Migration check output: $PENDING_MIGRATIONS" >> "$LOG_FILE"

# Log the full output of showmigrations
echo "Checking for pending migrations..." >> "$LOG_FILE"
poetry run python manage.py showmigrations >> "$LOG_FILE" 2>&1  # Logging full output to diagnose

# Check for unapplied migrations
PENDING_MIGRATIONS=$(poetry run python manage.py showmigrations | grep "\[ \]" | wc -l)  # Count unapplied migrations

if [ "$PENDING_MIGRATIONS" -gt 0 ]; then
    echo "Migrations found; stopping services..." >> "$LOG_FILE"
    sudo systemctl stop gunicorn-dev celery-indexer-worker-dev celery-beat-worker-dev celery-beat-dev

    echo 'Applying migrations...' >> "$LOG_FILE"
    poetry run python manage.py migrate >> "$LOG_FILE" 2>&1

    echo 'Starting services...' >> "$LOG_FILE"
    sudo systemctl start gunicorn-dev celery-indexer-worker-dev celery-beat-worker-dev celery-beat-dev
else
    echo 'No migrations found. Running collectstatic and restarting services...' >> "$LOG_FILE"
    poetry run python manage.py collectstatic --noinput >> "$LOG_FILE" 2>&1
    sudo systemctl restart gunicorn-dev celery-indexer-worker-dev celery-beat-worker-dev celery-beat-dev
fi

echo "$(date '+%Y-%m-%d %H:%M:%S') - after_install_dev.sh completed" >> "$LOG_FILE"




# #!/bin/bash
# # Log output to a specific file
# LOG_FILE="/home/ec2-user/django-indexer-dev/logs/deploy.log"

# # print placeholder
# echo -e "\n THIS IS A PLACEHOLDER \n" >> "$LOG_FILE"

# echo -e "\n\n" >> "$LOG_FILE"
# echo "=========================================" >> "$LOG_FILE"
# echo "Running after_install_dev.sh at $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG_FILE"
# echo "=========================================" >> "$LOG_FILE"

# # Load env vars
# source /home/ec2-user/.bashrc

# # Set correct ownership recursively for project directory
# sudo chown -R ec2-user:nginx /home/ec2-user/django-indexer/
# echo "$(date '+%Y-%m-%d %H:%M:%S') - Corrected ownership to ec2-user:nginx" >> "$LOG_FILE"

# # Set the necessary permissions
# sudo chmod -R 775 /home/ec2-user/django-indexer/
# echo "$(date '+%Y-%m-%d %H:%M:%S') - Set permissions to 775" >> "$LOG_FILE"

# # Restart nginx to apply any configuration changes
# sudo systemctl restart nginx
# echo "$(date '+%Y-%m-%d %H:%M:%S') - Restarted nginx" >> "$LOG_FILE"

# # Define the project directory
# PROJECT_DIR="/home/ec2-user/django-indexer"

# # Navigate to the project directory
# cd "$PROJECT_DIR"

# # Source the specific poetry virtual environment
# source "/home/ec2-user/.cache/pypoetry/virtualenvs/django-indexer-Y-SQFfhb-py3.11/bin/activate" # TODO: UPDATE THIS

# # Install dependencies using Poetry
# echo "$(date '+%Y-%m-%d %H:%M:%S') - Installing dependencies with Poetry" >> "$LOG_FILE"
# poetry install >> "$LOG_FILE"
# echo "$(date '+%Y-%m-%d %H:%M:%S') - Dependencies installed" >> "$LOG_FILE"

# # Check if there are pending migrations and log the output
# echo "Checking for pending migrations..." >> "$LOG_FILE"
# PENDING_MIGRATIONS=$(poetry run python manage.py showmigrations | grep '\[ \]' 2>&1)  # Redirect stderr to stdout
# echo "Migration check output: $PENDING_MIGRATIONS" >> "$LOG_FILE"

# # Log the full output of showmigrations
# echo "Checking for pending migrations..." >> "$LOG_FILE"
# poetry run python manage.py showmigrations >> "$LOG_FILE" 2>&1  # Logging full output to diagnose

# # Check for unapplied migrations
# PENDING_MIGRATIONS=$(poetry run python manage.py showmigrations | grep "\[ \]" | wc -l)  # Count unapplied migrations

# if [ "$PENDING_MIGRATIONS" -gt 0 ]; then
#     echo "Migrations found; stopping services..." >> "$LOG_FILE"
#     sudo systemctl stop gunicorn celery-indexer-worker celery-beat-worker celery-beat

#     echo 'Applying migrations...' >> "$LOG_FILE"
#     poetry run python manage.py migrate >> "$LOG_FILE" 2>&1

#     echo 'Starting services...' >> "$LOG_FILE"
#     sudo systemctl start gunicorn celery-indexer-worker celery-beat-worker celery-beat
# else
#     echo 'No migrations found. Running collectstatic and restarting services...' >> "$LOG_FILE"
#     poetry run python manage.py collectstatic --noinput >> "$LOG_FILE" 2>&1
#     sudo systemctl restart gunicorn celery-indexer-worker celery-beat-worker celery-beat
# fi

# echo "$(date '+%Y-%m-%d %H:%M:%S') - after_install_dev.sh completed" >> "$LOG_FILE"
