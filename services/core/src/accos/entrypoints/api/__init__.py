"""FastAPI inbound adapter."""

from __future__ import annotations

import logging
import sys

import uvicorn

from accos.entrypoints.api.application import create_app
from accos.kernel.errors import ConfigurationError
from accos.kernel.logging import configure_logging, get_logger, log_event
from accos.kernel.settings import load_settings

__all__ = ["create_app", "main"]


def main() -> int:
    """Load shared settings and run the HTTP server."""
    try:
        settings = load_settings()
    except ConfigurationError as error:
        sys.stderr.write(f"{error.code.value}: {error.public_message}\n")
        return 2
    configure_logging(
        settings.optional.log_level,
        service="accos-api",
        environment=settings.optional.environment,
    )
    log_event(
        get_logger("startup"),
        logging.INFO,
        "api_configuration_loaded",
        settings=settings.safe_summary(),
    )
    try:
        uvicorn.run(
            create_app(settings, configure_logs=False),
            host=settings.optional.api_host,
            port=settings.optional.api_port,
            log_config=None,
            access_log=False,
            loop="accos.kernel.asyncio:selector_loop_factory",
        )
    except KeyboardInterrupt:
        log_event(get_logger("startup"), logging.INFO, "api_shutdown_requested")
    return 0
