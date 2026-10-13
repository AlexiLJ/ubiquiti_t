import os
import time
from dataclasses import dataclass
from uuid import uuid4

import boto3
import httpx
import pytest
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError


@dataclass(frozen=True)
class Settings:
    # Keep the connection settings together; frozen=True prevents changing fields.
    endpoint: str
    console: str
    access_key: str
    secret_key: str
    region: str


@pytest.fixture(scope="session")
def settings():
    # Setting envs, settings object is shared throughout the test run.
    return Settings(
        endpoint=os.getenv("RUSTFS_ENDPOINT", "http://localhost:9000").rstrip("/"),
        console=os.getenv("RUSTFS_CONSOLE_URL", "http://localhost:9001/rustfs/console/auth/login/"),
        access_key=os.getenv("RUSTFS_ACCESS_KEY", "rustfsadmin"),
        secret_key=os.getenv("RUSTFS_SECRET_KEY", "rustfsadmin"),
        region=os.getenv("RUSTFS_REGION", "us-east-1"),
    )


@pytest.fixture(scope="session")
def http():
    # Share an HTTP client for health, management, and anonymous access requests.
    # trust_env=False ignores proxy settings that could redirect local requests.
    with httpx.Client(timeout=10, trust_env=False) as client:
        yield client


@pytest.fixture(scope="session")
def s3(settings):
    # Pytest supplies the settings fixture because it is named in the arguments.
    # Create one authenticated S3 client for bucket/object operations across the run.
    client = boto3.client(
        "s3",
        endpoint_url=settings.endpoint,
        aws_access_key_id=settings.access_key,
        aws_secret_access_key=settings.secret_key,
        region_name=settings.region,
        config=Config(
            # Use signed, path-style requests: localhost:9000/bucket/object.
            signature_version="s3v4",
            s3={"addressing_style": "path"},
            connect_timeout=3,
            read_timeout=10,
            retries={"max_attempts": 0},
            # Negotiate only required checksums for S3 compatibility. Object tests
            # also compare downloaded bytes with the original payload directly.
            request_checksum_calculation="when_required",
            response_checksum_validation="when_required",
        ),
    )
    # Yield the client for use, then close its connections when the session ends.
    yield client
    client.close()


@pytest.fixture(scope="session", autouse=True)
def service_ready(request, settings, http, s3):
    # Run automatically once before tests execute
    # Check that RustFS is usable before starting test operations.
    if request.config.getoption("collectonly"):
        return
    # A monotonic clock is unaffected by changes to the computer's wall clock.
    deadline = time.monotonic() + 90
    last_error = "Service did not become available"
    while time.monotonic() < deadline:
        try:
            response = http.get(f"{settings.endpoint}/health")
            response.raise_for_status()
            # authenticated S3 access should work
            s3.list_buckets()
            return
        except (httpx.HTTPError, BotoCoreError, ClientError) as error:
            # Retry only the startup check; the latest error is retained for diagnostics
            last_error = str(error)
            time.sleep(1)
    pytest.fail(f"RustFS not usable after 90s. Run docker compose up -d. Last error: {last_error}")


@pytest.fixture
def bucket(s3):
    # each requesting test gets its own fresh bucket.
    name = f"qa-{uuid4().hex}"
    s3.create_bucket(Bucket=name)

    yield name
    # Remove objects from every listing page, touching only this test's bucket.
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=name):
        # Key is an object's name. Bulk deletion expects a list of {"Key": name} entries.
        objects = [{"Key": obj["Key"]} for obj in page.get("Contents", [])]
        if objects:
            result = s3.delete_objects(Bucket=name, Delete={"Objects": objects})
            # Bulk deletion can partially fail even when the request succeeded.
            assert not result.get("Errors"), result.get("Errors")
    # S3 allows bucket deletion only after its objects have been removed.
    s3.delete_bucket(Bucket=name)
