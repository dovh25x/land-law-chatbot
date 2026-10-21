"""Run backend regressions with real httpx HTTP transports blocked, never models."""
import sys
from unittest.mock import patch

import httpx
import pytest


def forbidden(*args, **kwargs):
    raise AssertionError('Real HTTP transport forbidden in Phase3B offline checks')


async def async_forbidden(*args, **kwargs):
    raise AssertionError('Real HTTP transport forbidden in Phase3B offline checks')


with patch.object(httpx.HTTPTransport, 'handle_request', forbidden), \
        patch.object(httpx.AsyncHTTPTransport, 'handle_async_request', async_forbidden):
    raise SystemExit(pytest.main(['-q', *sys.argv[1:]]))
