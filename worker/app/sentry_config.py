"""Sentry error monitoring configuration.

Install: pip install sentry-sdk[fastapi]
Add SENTRY_DSN to environment variables.
"""
import os
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

def init_sentry():
    dsn = os.getenv("SENTRY_DSN")
    if not dsn:
        return
    sentry_sdk.init(
        dsn=dsn,
        environment=os.getenv("RENDER", "development"),
        traces_sample_rate=0.1,
        integrations=[FastApiIntegration()],
    )
