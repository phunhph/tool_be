# app/core/logging.py
from loguru import logger
import sys

logger.remove()
logger.add(
    sys.stdout,
    format="{time} | {level} | {name}:{function}:{line} | {message}",
    level="INFO"
)
logger.add(
    "logs/app_{time:YYYY-MM-DD}.log",
    rotation="00:00",
    retention="30 days",
    level="DEBUG"
)