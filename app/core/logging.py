import logging
import sys
from app.config import settings

def setup_logging():
    log_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("logs/app.log", encoding="utf-8") if not settings.DEBUG else logging.NullHandler()
        ]
    )
    logging.getLogger("uvicorn.access").disabled = not settings.DEBUG
    logging.getLogger("motor").setLevel(logging.WARNING)