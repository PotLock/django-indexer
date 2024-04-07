# Potlock Indexer (Django / Poetry / Celery / NEAR Lake Framework)

## Stack:

- Django w/ Poetry
- Celery for background indexer task

## Steps to run:

- Set up env vars via `~/.bashrc` or `~/.zshrc` (see below)
- Install poetry
- Install redis
- Install postgres
- Create postgres database `potlock` for user `postgres`
- Activate poetry shell (`poetry shell`)
- Install dependencies (`poetry install`)
- Run migrations (`python manage.py migrate`)
- Start celery worker with logger (`celery -A indexer worker --loglevel=info`)
- Start indexer (`python manage.py runindexer`)
- Kill indexer (`python manage.py killindexer`)
  - If for some reason this doesn't kill any active celery tasks, run `ps auxww | grep 'celery' | grep -v grep` and kill resulting PIDs

### Env vars example

```
export PL_POSTGRES_DB=potlock
export PL_POSTGRES_HOST=127.0.0.1
export PL_POSTGRES_PASS=
export PL_POSTGRES_PORT=5432
export PL_POSTGRES_USER=$USER
export PL_CELERY_BROKER_URL=redis://localhost:6379/0
export PL_AWS_ACCESS_KEY_ID=
export PL_AWS_SECRET_ACCESS_KEY=
```
