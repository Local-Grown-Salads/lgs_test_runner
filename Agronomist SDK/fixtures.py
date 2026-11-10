"""
Agronomist SDK test fixtures.

Hand-rolled setup/teardown for testing the agronomist-sdk.
"""

import os


def create():
    """Create and return the fixture instance.

    The Client will:
    - Read DATABASE_URL from env (set by docker-compose)
    - Auto-start PostgREST if targeting localhost
    - Wire up assembly/inspector departments
    """
    # Import here so repo_manager can load this file before deps are installed
    from lgs_agronomist_sdk import Client

    # Could add custom setup here:
    # - Set env vars
    # - Mock external services
    # - Seed additional test data

    return Client()


def teardown(fixture):
    """Clean up after test."""
    fixture.close()
