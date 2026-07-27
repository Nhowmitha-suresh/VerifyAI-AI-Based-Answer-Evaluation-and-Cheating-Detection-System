"""
Structured Logging Configuration for AI Proctoring Engine.
Directs system logs into logs/application.log, logs/events.log, and logs/errors.log.
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from backend.core.settings import settings

LOG_DIR = settings.LOG_DIR
os.makedirs(LOG_DIR, exist_ok=True)

APP_LOG_PATH = os.path.join(LOG_DIR, "application.log")
EVENT_LOG_PATH = os.path.join(LOG_DIR, "events.log")
ERROR_LOG_PATH = os.path.join(LOG_DIR, "errors.log")

formatter = logging.Formatter(
    "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Root Logger
logger = logging.getLogger("VerifyAI")
logger.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)

# Avoid duplicate handlers on re-initialization
if not logger.handlers:
    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Application File Handler
    app_handler = RotatingFileHandler(APP_LOG_PATH, maxBytes=5*1024*1024, backupCount=3, encoding="utf-8")
    app_handler.setLevel(logging.DEBUG)
    app_handler.setFormatter(formatter)
    logger.addHandler(app_handler)

    # Error File Handler
    error_handler = RotatingFileHandler(ERROR_LOG_PATH, maxBytes=5*1024*1024, backupCount=3, encoding="utf-8")
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)

# Dedicated Event Logger
event_logger = logging.getLogger("VerifyAI.Events")
event_logger.setLevel(logging.INFO)
if not event_logger.handlers:
    event_handler = RotatingFileHandler(EVENT_LOG_PATH, maxBytes=5*1024*1024, backupCount=5, encoding="utf-8")
    event_handler.setLevel(logging.INFO)
    event_handler.setFormatter(formatter)
    event_logger.addHandler(event_handler)
