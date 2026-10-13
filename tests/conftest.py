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


def pytest_addoption(parser):
    # hook for registering custom flags
    # store_true is False by default and True when --gui is supplied.
    parser.addoption("--gui", action="store_true", help="Run optional console test")


def pytest_collection_modifyitems(config, items):
    # This hook runs after test discovery and marks GUI tests as skipped by default.
    if not config.getoption("--gui"):
        for item in items:
            if "gui" in item.keywords:
                item.add_marker(pytest.mark.skip(reason="Enable optional console test with --gui"))


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
