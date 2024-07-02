- [Potlock Indexer (Django / Poetry / Celery / NEAR Lake Framework)](#potlock-indexer-django--poetry--celery--near-lake-framework)
  - [Stack:](#stack)
  - [Steps to run:](#steps-to-run)
    - [Env vars example](#env-vars-example)
  - [API Basics](#api-basics)
      - [Base URL](#base-url)
      - [Authorization](#authorization)
      - [Error Responses](#error-responses)
      - [Pagination](#pagination)
  - [API Endpoints](#api-endpoints)
    - [`Account` endpoints](#account-endpoints)
      - [✅ Get all accounts: `GET /accounts` (paginated)](#-get-all-accounts-get-accounts-paginated)
      - [✅ Get account by ID (address): `GET /accounts/{ACCOUNT_ID}`](#-get-account-by-id-address-get-accountsaccount_id)
      - [✅ Get donations received for account: `GET /accounts/{ACCOUNT_ID}/donations_received` (paginated)](#-get-donations-received-for-account-get-accountsaccount_iddonations_received-paginated)
      - [✅ Get donations sent for account: `GET /accounts/{ACCOUNT_ID}/donations_sent` (paginated)](#-get-donations-sent-for-account-get-accountsaccount_iddonations_sent-paginated)
      - [✅ Get pots for account: `GET /accounts/{ACCOUNT_ID}/active_pots` (paginated)](#-get-pots-for-account-get-accountsaccount_idactive_pots-paginated)
      - [✅ Get applications for account: `GET /accounts/{ACCOUNT_ID}/pot_applications` (paginated)](#-get-applications-for-account-get-accountsaccount_idpot_applications-paginated)
    - [`List` endpoints](#list-endpoints)
      - [✅ Get all lists: `GET /lists` (paginated)](#-get-all-lists-get-lists-paginated)
      - [✅ Get list by ID: `GET /lists/{LIST_ID}` (paginated)](#-get-list-by-id-get-listslist_id-paginated)
      - [✅ Get registrations for list: `GET /lists/{LIST_ID}/registrations` (paginated)](#-get-registrations-for-list-get-listslist_idregistrations-paginated)
      - [✅ Get random registration for list: `GET /lists/{LIST_ID}/random_registration`](#-get-random-registration-for-list-get-listslist_idrandom_registration)
    - [Donate Contract Config endpoint](#donate-contract-config-endpoint)
      - [✅ Get donate contract config: `GET /donate_contract_config`](#-get-donate-contract-config-get-donate_contract_config)
    - [`Donors` endpoints](#donors-endpoints)
      - [✅ Get all donors: `GET /donors` (paginated)](#-get-all-donors-get-donors-paginated)
    - [`Pots` endpoints](#pots-endpoints)
      - [✅ Get all pots: `GET /pots` (paginated)](#-get-all-pots-get-pots-paginated)
      - [✅ Get applications for pot: `GET /pots/{POT_ID}/applications`](#-get-applications-for-pot-get-potspot_idapplications)
      - [✅ Get donations for pot: `GET /pots/{POT_ID}/donations`](#-get-donations-for-pot-get-potspot_iddonations)
      - [✅ Get sponsors for pot: `GET /pots/{POT_ID}/sponsors`](#-get-sponsors-for-pot-get-potspot_idsponsors)
      - [✅ Get payouts for pot: `GET /pots/{POT_ID}/payouts`](#-get-payouts-for-pot-get-potspot_idpayouts)
    - [`Stats` endpoints](#stats-endpoints)
      - [✅ Get stats: `GET /stats`](#-get-stats-get-stats)

# Potlock Indexer (Django / Poetry / Celery / NEAR Lake Framework)

## Stack:

- Django w/ Poetry
- Celery for background indexer task
- NEAR Data Lake Framework for fetching/listening for blocks

## Steps to run:

- Set up env vars via `~/.bashrc` or `~/.zshrc` (see below)
- Install poetry
- Install redis
- Install postgres
- Create postgres database `potlock` for user `postgres`
- Activate poetry shell (`poetry shell`)
- Install dependencies (`poetry install`)
- Run migrations (`python manage.py migrate`)
- Update `indexer_app.tasks.listen_to_near_events` with desired network & start block (if desired)
- Start celery worker with logger (`celery -A base worker --loglevel=info`)
- Start indexer (`python manage.py runindexer`)
- Kill indexer (`python manage.py killindexer`)
  - If for some reason this doesn't kill any active celery tasks, run `ps auxww | grep 'celery' | grep -v grep` and kill resulting PIDs

Extra commands that might come in useful:

- Purge celery queue (`celery -A base purge`)

### Env vars example

```
export PL_AWS_ACCESS_KEY_ID=
export PL_AWS_SECRET_ACCESS_KEY=
export PL_CACHALOT_ENABLED=False
export PL_DEBUG=True
export PL_ENVIRONMENT=local
export PL_LOG_LEVEL=debug
export PL_POSTGRES_DB=potlock
export PL_POSTGRES_HOST=127.0.0.1
export PL_POSTGRES_PASS=
export PL_POSTGRES_PORT=5432
export PL_POSTGRES_USER=$USER
export PL_REDIS_HOST=
export PL_REDIS_PORT=6379
export PL_SENTRY_DSN=
```

## API Basics

#### Base URL

**dev (mainnet):** `https://dev.potlock.io/api/v1/`
**testnet:** `https://test-dev.potlock.io/api/v1/`

#### Authorization

This is a public, read-only API and as such does not currently implement authentication or authorization.

Rate limits of 500 requests/min are enforced to ensure service for all users.

#### Error Responses

An error response (status code not within range 200-299) will always contain an object body with a `message` string property containing more information about the error.

Possible Error Codes:

- **`400` (Bad Request)**
  - Error in client request
- **`404` (Not found)**
  - Requested resource could not be located
- **`500` (Internal Error)**
  - Check `message` string for more information

#### Pagination

Pagination available using `limit` and `offset` query params on endpoints that specify `paginated`. Default `limit` is 30.

Endpoints that support pagination will return a success response containing the following:

- `count` (int) - total number of items available
- `next` (str | null) - pre-populated endpoint link to the next page of results
- `previous` (str | null) - pre-populated endpoint link to the previous page of results
- `results` (any[]) - array of results

## API Endpoints

_NB: These endpoints are what is required to integrate with BOS app & replace current RPC calls, but more endpoints can easily be added as needed._

### `Account` endpoints

#### ✅ Get all accounts: `GET /accounts` (paginated)

#### ✅ Get account by ID (address): `GET /accounts/{ACCOUNT_ID}`

#### ✅ Get donations received for account: `GET /accounts/{ACCOUNT_ID}/donations_received` (paginated)

#### ✅ Get donations sent for account: `GET /accounts/{ACCOUNT_ID}/donations_sent` (paginated)

#### ✅ Get pots for account: `GET /accounts/{ACCOUNT_ID}/active_pots` (paginated)

Can specify `status=live` query param to retrieve only pots that are currently active (live matching round)

#### ✅ Get applications for account: `GET /accounts/{ACCOUNT_ID}/pot_applications` (paginated)

Can specify `status={PotApplicationStatus}` query param to retrieve applications with a given status:

```py
enum PotApplicationStatus {
  Pending,
  Approved,
  Rejected,
  InReview,
}
```

### `List` endpoints

#### ✅ Get all lists: `GET /lists` (paginated)

#### ✅ Get list by ID: `GET /lists/{LIST_ID}` (paginated)

#### ✅ Get registrations for list: `GET /lists/{LIST_ID}/registrations` (paginated)

Can specify status to filter by using `status` query param if desired, e.g. `status=Approved`
Can also specify project category to filter by using `category` query param if desired, e.g. `category=Education`

#### ✅ Get random registration for list: `GET /lists/{LIST_ID}/random_registration`

Can specify status to filter by using `status` query param if desired, e.g. `status=Approved`

### Donate Contract Config endpoint

#### ✅ Get donate contract config: `GET /donate_contract_config`

### `Donors` endpoints

#### ✅ Get all donors: `GET /donors` (paginated)

Returns all accounts that have sent at least one donation.

Optional query params:

- `sort` (currently only allowed value is `most_donated_usd`, which returns results in the order of most to least donated in USD) e.g. `?sort=most_donated_usd`

### `Pots` endpoints

_NB: `POT_ID` == on-chain Pot address_

#### ✅ Get all pots: `GET /pots` (paginated)

#### ✅ Get applications for pot: `GET /pots/{POT_ID}/applications`

#### ✅ Get donations for pot: `GET /pots/{POT_ID}/donations`

#### ✅ Get sponsors for pot: `GET /pots/{POT_ID}/sponsors`

#### ✅ Get payouts for pot: `GET /pots/{POT_ID}/payouts`

### `Stats` endpoints

#### ✅ Get stats: `GET /stats`

Returns:

- `total_donations_usd`
- `total_payouts_usd`
- `total_donations_count`
- `total_donors_count`
- `total_recipients_count`
