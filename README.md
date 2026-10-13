# RustFS storage QA take-home

A small risk-based integration suite using pytest, boto3 for S3, HTTP requests signed
with botocore for management, and Playwright for one console smoke test.
uv manages dependencies; commit `uv.lock` alongside the source.

## Setup and execution

Prerequisites: Python 3.12+, uv, and Docker Compose v2 with a running Linux container engine.

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
uv run playwright install chromium
docker compose up -d --wait --wait-timeout 180
uv run pytest
```

`uv sync` creates the project's `.venv` and installs the locked dependencies.
You do not need to activate the virtual environment before using `uv run`.
The Playwright installation command downloads Chromium for the console test.

After setup, `uv run pytest` is the single command for the required suite. Tests wait
up to 90 seconds for liveness and an authenticated S3 request to succeed. A missing
service causes a setup error, rather than a misleading skip. Requests have bounded
timeouts and SDK retries are disabled, so unexpected failures remain visible.

The console smoke test runs with the default suite. It opens
`http://localhost:9001/rustfs/console/auth/login/`,
signs in and verifies that the API-created test bucket appears in the console.
This single journey checks console accessibility, authentication and API/UI consistency.
It is marked with `smoke` so it can also be selected separately.

Run the smoke test with installed Chrome in **headless mode** (no browser window):

```powershell
uv run pytest -m smoke --browser chromium --browser-channel chrome
```

To watch the browser open and perform actions, use **headed mode**. `--slowmo 500`
slows Playwright actions by 500 milliseconds so you can follow them:

```powershell
uv run pytest -m smoke --browser chromium --browser-channel chrome --headed --slowmo 500
```

To run only the console test with the Chromium installed during setup:

```sh
uv run pytest -m smoke --browser chromium
```

Playwright runs headless by default; `--headed` enables a visible browser window.
No opt-in flag is needed for the console test. `-m smoke` selects smoke tests;
currently the console test is the only smoke test.
pytest-playwright provides an isolated browser context for each test.
Add `--tracing retain-on-failure --screenshot only-on-failure` to any GUI command
to save failure artifacts in `test-results/`.

Useful commands:

```sh
uv run pytest -m data
uv run pytest -m management
uv run pytest --collect-only
uv run pytest --junitxml=test-results/results.xml
uv run ruff check tests
docker compose logs rustfs
docker compose down
```

`docker compose down` retains storage volumes. `docker compose down -v` removes all
data belonging to this Compose project; use it only when deliberately resetting
the local test instance.
