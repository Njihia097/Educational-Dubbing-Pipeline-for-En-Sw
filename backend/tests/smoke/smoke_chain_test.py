"""
================================================================================
 SMOKE TEST — New Architecture
 External AI Microservice + Celery Chain + MinIO + Backend API
================================================================================

This script validates the entire pipeline:

    1. Starts job through backend /api/jobs/create
    2. Uploads input video → MinIO
    3. Backend schedules Celery chain
    4. Worker calls EXTERNAL_AI microservice for:
         ASR → Punctuate → MT → TTS → Demucs → Mix → Mux
    5. Output uploaded to MinIO
    6. Job reaches "completed"

Run with:
    $env:PYTHONPATH="."; python backend/tests/smoke/smoke_chain_test.py
    PYTHONPATH=. python backend/tests/smoke/smoke_chain_test.py

Requires:
    • external_ai running locally
    • docker compose up (backend + worker + redis + minio + postgres)
    • demo.mp4 present under storage/uploads/demo.mp4
================================================================================
"""

import os
import time
import json
import requests
from pathlib import Path


# CONFIG -----------------------------------------------------------------------
BACKEND = os.getenv("BACKEND_URL", "http://localhost:5000")

# Your input test file (prefer env override, then repo path, then container volume)
TEST_VIDEO = Path(
    os.getenv("SMOKE_TEST_VIDEO", "storage/uploads/demo.mp4")
)
if not TEST_VIDEO.exists():
    possible = Path("/data/uploads/demo.mp4")
    if possible.exists():
        TEST_VIDEO = possible

POLL_INTERVAL = 3
POLL_TIMEOUT = 600  # 10 minutes


def print_banner(title):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80 + "\n")


# STEP 1 — CREATE TEST JOB -----------------------------------------------------
def create_job():
    print_banner("STEP 1: Creating test job via /api/jobs/create")

    if not TEST_VIDEO.exists():
        raise FileNotFoundError(
            f"❌ demo.mp4 file missing: {TEST_VIDEO}\n"
            f"Place it under storage/uploads/demo.mp4"
        )

    # Prepare form-data upload
    files = {"file": open(TEST_VIDEO, "rb")}
    data = {
        "owner_id": "1",    # OK for smoke tests since user gets created automatically
        "project_id": "1",  # OK for smoke tests
    }

    r = requests.post(f"{BACKEND}/api/jobs/create", files=files, data=data)
    print(f"Response: {r.status_code}")
    print(r.text)

    if r.status_code != 201:
        raise RuntimeError("❌ Job creation failed.")

    j = r.json()
    print("\n🎉 Job created")
    print(f"  Job ID      : {j['job_id']}")
    print(f"  Celery Task : {j['task_id']}")
    print(f"  Input URI   : {j['uri']}")

    return j["job_id"], j["task_id"], j["uri"]


# STEP 2 — POLL UNTIL COMPLETED ------------------------------------------------
def poll_job(job_id):
    print_banner("STEP 2: Polling job status until completed")

    start = time.time()
    last_state = None

    while True:
        r = requests.get(f"{BACKEND}/api/jobs/status/{job_id}")
        if r.status_code != 200:
            raise RuntimeError("❌ Could not fetch job status")

        info = r.json()
        state = info.get("state")
        step = info.get("current_step")

        if state != last_state:
            print(f"➡️ State changed → {state} | Step: {step}")
            last_state = state

        # End states
        if state in ("completed", "failed"):
            return info

        if time.time() - start > POLL_TIMEOUT:
            raise TimeoutError("❌ Pipeline did not finish in time")

        time.sleep(POLL_INTERVAL)


# STEP 3 — SUMMARY -------------------------------------------------------------
def summarize(info):
    print_banner("STEP 3: Pipeline Summary")

    print(json.dumps(info, indent=2))

    if info["state"] == "completed":
        print("\n🎉 SUCCESS: Pipeline completed successfully")
    else:
        print("\n❌ FAILURE: Pipeline failed. Check worker logs.")

    print("\nSteps executed:")
    for s in info.get("steps", []):
        print(f" • {s['name']} → {s['state']}")

    print("\nCheck MinIO buckets:")
    print(" - uploads/")
    print(" - outputs/")
    print(" - intermediate JSON + WAV files")

    print("\nSmoke test complete.\n")


# MAIN -------------------------------------------------------------------------
if __name__ == "__main__":
    print_banner("🚀 Starting Complete Smoke Test for New Architecture")

    job_id, task_id, uri = create_job()
    print(f"Submitted Job ID: {job_id}")
    print(f"Celery Root Task: {task_id}")

    info = poll_job(job_id)
    summarize(info)
