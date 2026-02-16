from __future__ import annotations

import logging


def configure_logging() -> None:
    """Simple, dev-friendly logging setup.

    Uvicorn config can override this, but this gives us sane defaults when running locally.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
