# RustFS storage QA take-home

A small risk-based integration suite using pytest, boto3 for S3, HTTP requests signed
with botocore for management, and Playwright for one console smoke test.
uv manages dependencies; commit `uv.lock` alongside the source.

## Setup and execution

Prerequisites: Python 3.12+, uv, Google Chrome, and Docker Compose v2 with a running
Linux container engine.

Install uv first; it can install Python even if Python is not already installed.
On Windows, open PowerShell and run:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

On macOS or Linux, open a terminal and run:

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Close and reopen the terminal after installation so the updated PATH is available.
Verify uv and install Python 3.12 (these commands work on all three platforms):

```sh
uv --version
uv python install 3.12
uv python find 3.12
```

The last command prints the installed Python interpreter's path. A separate Python
installer is not required when using uv. See the official
[uv installation guide](https://docs.astral.sh/uv/getting-started/installation/) and
[Python installation guide](https://docs.astral.sh/uv/guides/install-python/) for details.

Docker must be running before you start the services or run the tests. On Windows
or macOS, open Docker Desktop and wait until its engine is running; use Linux
containers for this project. On Linux, ensure the Docker daemon is running.
Keep Docker running throughout the test run.

Open a terminal in this project's directory (the folder
containing `pyproject.toml` and `docker-compose.yml`) and run:

```sh
uv sync --locked --python 3.12
docker compose up -d --wait --wait-timeout 180
uv run pytest --browser-channel chrome --headed
```

`uv sync` creates the project's `.venv` and installs the locked dependencies.
You do not need to activate the virtual environment before using `uv run`.

The test command above runs the full suite and opens Google Chrome for the console
test. Tests wait up to 90 seconds for liveness and an authenticated S3 request to
succeed. A missing service causes a setup error. Requests have bounded timeouts
and SDK retries are disabled, so unexpected failures remain visible.

The console smoke test runs with the default suite. It opens
`http://localhost:9001/rustfs/console/auth/login/`,
signs in and verifies that the API-created test bucket appears in the console.
This single journey checks console accessibility, authentication and API/UI consistency.
pytest-playwright provides an isolated browser context for each test.

## Test coverage

**Implemented** means the test contains executable checks. **SPEC** means the
scenario is documented but its test body currently contains only `pass`.
Specification-only cases can appear as passing in pytest without verifying the
described behavior; they are not counted as implemented coverage.

| Area / marker | Test | Coverage or specified behavior | Cases | Status |
| --- | --- | --- | --- | --- |
| Data (`data`) | `test_object_integrity_and_metadata` | Empty and 1 MiB binary objects; exact downloaded bytes, size, content type, metadata, and a key containing spaces/Unicode | 2 | Implemented |
| Data (`data`) | `test_overwrite_and_delete` | Shorter overwrite, exact replacement bytes, missing-object error after deletion, and repeated deletion | 1 | Implemented |
| Data (`data`) | `test_listing_prefix_and_pagination` | Prefix filtering and complete listings across pages without missing or duplicate keys | 1 | **SPEC** |
| Data (`data`) | `test_nonempty_bucket_cannot_be_deleted` | Reject nonempty bucket deletion with BucketNotEmpty/409 and verify the object survives intact | 1 | Implemented |
| Data (`data`) | `test_private_object_rejects_anonymous_read` | Reject an unsigned private-object download with AccessDenied/403 and prevent payload disclosure | 1 | Implemented |
| Management (`management`) | `test_health` | Successful liveness and readiness responses from `/health` and `/health/ready` | 2 | Implemented |
| Management (`management`) | `test_admin_reports_server_and_storage` | Signed admin server-info request; online servers, healthy drives, four online disks, and no offline disks | 1 | Implemented |
| Management (`management`) | `test_admin_rejects_invalid_authentication` | Reject unsigned and incorrectly signed admin requests without exposing server information | 2 | Implemented |
| Console (`smoke`) | `test_console_smoke` | Browser login and visibility of the unique bucket created through the S3 API | 1 | Implemented |
| Resilience (`data`) | `test_data_available_when_one_node_is_offline` | Existing data remains intact and new writes succeed when surviving nodes retain read/write quorum | 1 | **SPEC** |
| Resilience (`data`) | `test_data_operations_when_half_of_nodes_are_offline` | Read/write outcomes match the configured quorum when half the nodes are unavailable; data survives recovery | 1 | **SPEC** |
| Resilience (`data`) | `test_writes_rejected_when_quorum_is_lost` | Reject writes without write quorum and verify original data after recovery | 1 | **SPEC** |
| Resilience (`data`) | `test_recovered_node_synchronizes_missed_changes` | Recover creates, overwrites, and deletes made during an outage without stale or resurrected objects | 1 | **SPEC** |
| Resilience (`data`) | `test_object_synchronization_between_nodes` | Consistent contents, metadata, and listings across node endpoints after creates, overwrites, and deletes | 1 | **SPEC** |
| Resilience (`data`) | `test_network_partition_preserves_acknowledged_data` | Quorum-dependent behavior during a network partition and preservation of acknowledged writes after recovery | 1 | **SPEC** |

There are **11 implemented cases** and **7 specification-only cases**, for **18
collected cases** after parameterization. The six resilience specifications require
a multi-node cluster; node failures and network partitions also need controlled
failure injection. The current Compose deployment has one RustFS node with four
storage volumes.

## Remarks

I used Codex to assist with API research, documentation (including this README), and parts of the test implementation.

With three hours available, I focused on implementing the core checks and
documenting additional scenarios as specifications. These show the coverage I
would add next and how I approach test design.

I have also used S3 for my blog. In an earlier
[blog post](https://leginabroad.com/tech/script-for-back-up-posgresql-database),
I described automating PostgreSQL database backups, uploading them to an S3 bucket,
and scheduling the job to run monthly.
