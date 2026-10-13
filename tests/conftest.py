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


