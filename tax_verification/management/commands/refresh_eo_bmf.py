import csv
import hashlib
import logging
import os
import tempfile
import time

import requests
from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.utils import timezone

from tax_verification.models import NonprofitRegistry

logger = logging.getLogger("jobs")

EO_BMF_URLS = [
    "https://www.irs.gov/pub/irs-soi/eo1.csv",
    "https://www.irs.gov/pub/irs-soi/eo2.csv",
    "https://www.irs.gov/pub/irs-soi/eo3.csv",
    "https://www.irs.gov/pub/irs-soi/eo4.csv",
]

EXPECTED_HEADERS = [
    "EIN", "NAME", "ICO", "STREET", "CITY", "STATE", "ZIP", "GROUP",
    "SUBSECTION", "AFFILIATION", "CLASSIFICATION", "RULING", "DEDUCTIBILITY",
    "FOUNDATION", "ACTIVITY", "ORGANIZATION", "STATUS", "TAX_PERIOD",
    "ASSET_CD", "INCOME_CD", "FILING_REQ_CD", "PF_FILING_REQ_CD", "ACCT_PD",
    "ASSET_AMT", "INCOME_AMT", "REVENUE_AMT", "NTEE_CD", "SORT_NAME",
]

CHUNK_SIZE = 5000
LOCK_KEY = "eo_bmf_refresh_lock"
LOCK_TIMEOUT = 45 * 60  # 45 minutes


def compute_row_hash(row):
    key_fields = "|".join([
        row.get("EIN", ""),
        row.get("NAME", ""),
        row.get("SUBSECTION", ""),
        row.get("DEDUCTIBILITY", ""),
        row.get("STATUS", ""),
        row.get("CITY", ""),
        row.get("STATE", ""),
        row.get("RULING", ""),
        row.get("NTEE_CD", ""),
        row.get("FOUNDATION", ""),
        row.get("ASSET_AMT", ""),
        row.get("INCOME_AMT", ""),
        row.get("REVENUE_AMT", ""),
    ])
    return hashlib.md5(key_fields.encode("latin-1", errors="replace")).hexdigest()


def download_file(url, dest_path, max_retries=3):
    for attempt in range(max_retries):
        try:
            logger.info(f"Downloading {url} (attempt {attempt + 1})...")
            resp = requests.get(url, stream=True, timeout=120)
            resp.raise_for_status()
            with open(dest_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            file_size = os.path.getsize(dest_path)
            logger.info(f"Downloaded {url} ({file_size / 1024 / 1024:.1f} MB)")
            return True
        except Exception as e:
            wait = 5 * (3 ** attempt)  # 5s, 15s, 45s
            logger.warning(f"Download failed for {url}: {e}. Retrying in {wait}s...")
            time.sleep(wait)
    logger.error(f"All {max_retries} download attempts failed for {url}")
    return False


def validate_csv_headers(file_path):
    with open(file_path, "r", encoding="latin-1") as f:
        reader = csv.reader(f)
        headers = next(reader)
        headers = [h.strip() for h in headers]
    if headers != EXPECTED_HEADERS:
        logger.error(f"Header mismatch in {file_path}. Got: {headers}")
        return False
    return True


def row_to_model_kwargs(row):
    return {
        "ein": row.get("EIN", "").strip(),
        "name": row.get("NAME", "").strip(),
        "ico": row.get("ICO", "").strip(),
        "street": row.get("STREET", "").strip(),
        "city": row.get("CITY", "").strip(),
        "state": row.get("STATE", "").strip(),
        "zip": row.get("ZIP", "").strip(),
        "group": row.get("GROUP", "").strip(),
        "subsection": row.get("SUBSECTION", "").strip(),
        "affiliation": row.get("AFFILIATION", "").strip(),
        "classification": row.get("CLASSIFICATION", "").strip(),
        "ruling": row.get("RULING", "").strip(),
        "deductibility": row.get("DEDUCTIBILITY", "").strip(),
        "foundation": row.get("FOUNDATION", "").strip(),
        "activity": row.get("ACTIVITY", "").strip(),
        "organization": row.get("ORGANIZATION", "").strip(),
        "status": row.get("STATUS", "").strip(),
        "tax_period": row.get("TAX_PERIOD", "").strip(),
        "asset_cd": row.get("ASSET_CD", "").strip(),
        "income_cd": row.get("INCOME_CD", "").strip(),
        "filing_req_cd": row.get("FILING_REQ_CD", "").strip(),
        "pf_filing_req_cd": row.get("PF_FILING_REQ_CD", "").strip(),
        "acct_pd": row.get("ACCT_PD", "").strip(),
        "asset_amt": row.get("ASSET_AMT", "").strip(),
        "income_amt": row.get("INCOME_AMT", "").strip(),
        "revenue_amt": row.get("REVENUE_AMT", "").strip(),
        "ntee_cd": row.get("NTEE_CD", "").strip(),
        "sort_name": row.get("SORT_NAME", "").strip(),
    }


class Command(BaseCommand):
    help = "Download and import IRS EO BMF data into NonprofitRegistry"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Limit total rows processed per file (for testing)",
        )
        parser.add_argument(
            "--files",
            type=str,
            default=None,
            help="Comma-separated file numbers to download (e.g. '4' or '1,2'). Default: all 4.",
        )

    def handle(self, *args, **options):
        limit = options.get("limit")
        files_arg = options.get("files")
        if files_arg:
            file_nums = [int(x.strip()) for x in files_arg.split(",")]
            urls = [u for u in EO_BMF_URLS if int(u.split("eo")[-1].split(".")[0]) in file_nums]
        else:
            urls = EO_BMF_URLS
        # Acquire distributed lock
        if not cache.add(LOCK_KEY, "running", LOCK_TIMEOUT):
            logger.warning("EO BMF refresh already running (lock held). Exiting.")
            self.stdout.write("Another refresh is already running.")
            return

        start_time = time.time()
        logger.info("Starting IRS EO BMF refresh...")

        stats = {"inserted": 0, "updated": 0, "unchanged": 0, "skipped": 0, "deleted": 0}
        seen_eins = set()
        tmp_dir = tempfile.mkdtemp()

        try:
            # Step 1: Download all 4 files
            file_paths = []
            for url in urls:
                filename = url.split("/")[-1]
                dest = os.path.join(tmp_dir, filename)
                if not download_file(url, dest):
                    logger.error(f"Failed to download {url}. Aborting entire refresh.")
                    return
                if not validate_csv_headers(dest):
                    logger.error(f"Invalid headers in {dest}. Aborting entire refresh.")
                    return
                file_paths.append(dest)

            # Load existing hashes for comparison
            logger.info("Loading existing EIN hashes from database...")
            existing_hashes = dict(
                NonprofitRegistry.objects.values_list("ein", "data_hash")
            )
            logger.info(f"Loaded {len(existing_hashes)} existing records.")

            # Step 2-3: Process each file in chunks
            for file_path in file_paths:
                file_start = time.time()
                filename = os.path.basename(file_path)
                file_rows = 0
                file_errors = 0
                chunk = []

                with open(file_path, "r", encoding="latin-1") as f:
                    reader = csv.DictReader(f)
                    for line_num, row in enumerate(reader, start=2):
                        if limit is not None and file_rows >= limit:
                            break
                        # Validate row has EIN
                        ein = row.get("EIN", "").strip()
                        if not ein:
                            file_errors += 1
                            logger.warning(f"{filename}:{line_num} - Missing EIN, skipping.")
                            stats["skipped"] += 1
                            continue

                        seen_eins.add(ein)
                        file_rows += 1
                        data_hash = compute_row_hash(row)

                        # Check if record exists and hash matches
                        if ein in existing_hashes and existing_hashes[ein] == data_hash:
                            stats["unchanged"] += 1
                            continue

                        kwargs = row_to_model_kwargs(row)
                        kwargs["data_hash"] = data_hash
                        chunk.append(NonprofitRegistry(**kwargs))

                        if ein in existing_hashes:
                            stats["updated"] += 1
                        else:
                            stats["inserted"] += 1

                        if len(chunk) >= CHUNK_SIZE:
                            self._upsert_chunk(chunk)
                            chunk = []

                # Flush remaining chunk
                if chunk:
                    self._upsert_chunk(chunk)

                # Check for high error rate
                if file_rows > 0 and file_errors / file_rows > 0.01:
                    logger.error(
                        f"{filename}: {file_errors}/{file_rows} rows malformed (>{1}%). Aborting."
                    )
                    return

                file_duration = time.time() - file_start
                logger.info(
                    f"{filename}: {file_rows} rows processed in {file_duration:.1f}s, "
                    f"{file_errors} errors"
                )

            # Step 4: Delete orgs no longer in IRS data (only on full runs)
            is_full_run = limit is None and len(urls) == len(EO_BMF_URLS)
            if is_full_run and seen_eins:
                deleted_count, _ = NonprofitRegistry.objects.exclude(
                    ein__in=seen_eins
                ).delete()
                stats["deleted"] = deleted_count
            elif not is_full_run:
                logger.info("Partial run (--limit or --files used); skipping delete step.")

            duration = time.time() - start_time
            logger.info(
                f"EO BMF refresh complete in {duration:.1f}s. "
                f"Inserted: {stats['inserted']}, Updated: {stats['updated']}, "
                f"Unchanged: {stats['unchanged']}, Deleted: {stats['deleted']}, "
                f"Skipped: {stats['skipped']}"
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"EO BMF refresh complete. "
                    f"Inserted: {stats['inserted']}, Updated: {stats['updated']}, "
                    f"Unchanged: {stats['unchanged']}, Deleted: {stats['deleted']}"
                )
            )

        except Exception as e:
            logger.error(f"EO BMF refresh failed: {e}")
            raise
        finally:
            # Cleanup temp files
            for url in urls:
                filename = url.split("/")[-1]
                path = os.path.join(tmp_dir, filename)
                if os.path.exists(path):
                    os.remove(path)
            try:
                os.rmdir(tmp_dir)
            except OSError:
                pass
            # Release lock
            cache.delete(LOCK_KEY)

    def _upsert_chunk(self, chunk):
        update_fields = [
            "name", "ico", "street", "city", "state", "zip", "group",
            "subsection", "affiliation", "classification", "ruling",
            "deductibility", "foundation", "activity", "organization",
            "status", "tax_period", "asset_cd", "income_cd", "filing_req_cd",
            "pf_filing_req_cd", "acct_pd", "asset_amt", "income_amt",
            "revenue_amt", "ntee_cd", "sort_name", "data_hash", "last_updated",
        ]
        NonprofitRegistry.objects.bulk_create(
            chunk,
            update_conflicts=True,
            unique_fields=["ein"],
            update_fields=update_fields,
        )
