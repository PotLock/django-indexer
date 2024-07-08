#!/bin/bash
# Log output to a specific file
LOG_FILE="/home/ec2-user/django-indexer-testnet/logs/deploy.log"

echo -e "\n\n" >> "$LOG_FILE"
echo "=========================================" >> "$LOG_FILE"
echo "Running after_install_testnet.sh at $(date '+%Y-%m-%d %H:%M:%S')" >> "$LOG_FILE"
echo "=========================================" >> "$LOG_FILE"

# Load env vars
export PL_ENVIRONMENT=testnet
source /home/ec2-user/.bashrc

# Set correct ownership recursively for project directory
sudo chown -R ec2-user:nginx /home/ec2-user/django-indexer-testnet/
echo "$(date '+%Y-%m-%d %H:%M:%S') - Corrected ownership to ec2-user:nginx" >> "$LOG_FILE"

# Set the necessary permissions
sudo chmod -R 775 /home/ec2-user/django-indexer-testnet/
echo "$(date '+%Y-%m-%d %H:%M:%S') - Set permissions to 775" >> "$LOG_FILE"

# Restart nginx to apply any configuration changes
sudo systemctl restart nginx
echo "$(date '+%Y-%m-%d %H:%M:%S') - Restarted nginx" >> "$LOG_FILE"

# Define the project directory
PROJECT_DIR="/home/ec2-user/django-indexer-testnet"

# Navigate to the project directory
cd "$PROJECT_DIR"

# Source the specific poetry virtual environment
source "/home/ec2-user/.cache/pypoetry/virtualenvs/django-indexer-AhfQkQzj-py3.11/bin/activate"

# Install dependencies using Poetry
echo "$(date '+%Y-%m-%d %H:%M:%S') - Installing dependencies with Poetry" >> "$LOG_FILE"
poetry lock --no-update >> "$LOG_FILE"
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
    # COMMENTING OUT FOR NOW AS I BELIEVE STOPPING SERVICES IS UNNECESSARY
    # echo "Migrations found; stopping services..." >> "$LOG_FILE"
    # sudo systemctl stop gunicorn-testnet celery-indexer-worker-testnet celery-beat-worker-testnet celery-beat-testnet

    echo 'Applying migrations...' >> "$LOG_FILE"
    poetry run python manage.py migrate >> "$LOG_FILE" 2>&1
else
    echo 'No migrations found.' >> "$LOG_FILE"
fi

# Collect static
echo 'Running collectstatic...' >> "$LOG_FILE"
poetry run python manage.py collectstatic --noinput >> "$LOG_FILE" 2>&1

# Gracefully reload Gunicorn to apply the changes without downtime
echo 'Reloading Gunicorn...' >> "$LOG_FILE"
sudo systemctl kill --signal=HUP gunicorn-testnet

echo 'Restarting services...' >> "$LOG_FILE"
sudo systemctl restart celery-indexer-worker-testnet celery-beat-worker-testnet celery-beat-testnet

echo "$(date '+%Y-%m-%d %H:%M:%S') - after_install_testnet.sh completed" >> "$LOG_FILE"
