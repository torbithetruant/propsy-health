"""
Centralized logging configuration for Propsy Health OAuth Connector.

Features:
- Structured logging with timestamps, levels, and module names
- Color-coded console output for development
- JSON logging for production (ELK/Datadog compatible)
- Sensitive data filtering (tokens, secrets never logged)
- Log rotation for production
- Configurable via LOG_LEVEL and LOG_FORMAT in .env
"""
import logging
import logging.handlers
import re
import sys
from pathlib import Path
from typing import Any

from app.config import get_settings


# ============================================================================
# SENSITIVE DATA FILTER - Prevents tokens/secrets from appearing in logs
# ============================================================================

class SensitiveDataFilter(logging.Filter):
    """
    Filter that redacts sensitive information from log messages.
    
    Redacts:
    - OAuth tokens (access_token, refresh_token)
    - Bearer tokens
    - API keys
    - Passwords
    - JWT tokens
    """
    
    # Patterns to redact (compiled for performance)
    PATTERNS = [
        # OAuth tokens
        (re.compile(r'(access_token["\s:=]+)["\']?([A-Za-z0-9\-_.]{20,})["\']?', re.IGNORECASE), r'\1[REDACTED]'),
        (re.compile(r'(refresh_token["\s:=]+)["\']?([A-Za-z0-9\-_.]{20,})["\']?', re.IGNORECASE), r'\1[REDACTED]'),
        # Bearer tokens in headers
        (re.compile(r'(Bearer\s+)([A-Za-z0-9\-_.]+)', re.IGNORECASE), r'\1[REDACTED]'),
        # JWT tokens
        (re.compile(r'(eyJ[A-Za-z0-9\-_]+\.eyJ[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+)'), '[REDACTED_JWT]'),
        # API keys (generic)
        (re.compile(r'(api[_-]?key["\s:=]+)["\']?([A-Za-z0-9\-_]{20,})["\']?', re.IGNORECASE), r'\1[REDACTED]'),
        # Passwords
        (re.compile(r'(password["\s:=]+)["\']?([^"\s,}]+)["\']?', re.IGNORECASE), r'\1[REDACTED]'),
        # Google OAuth codes
        (re.compile(r'(code=)([A-Za-z0-9\-_/]{20,})'), r'\1[REDACTED]'),
        # Fernet encrypted tokens (start with gAAAA)
        (re.compile(r'gAAAAAB[A-Za-z0-9\-_]{50,}'), '[REDACTED_ENCRYPTED]'),
    ]
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Apply redaction to log messages."""
        if isinstance(record.msg, str):
            record.msg = self._redact(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: self._redact_value(v) for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(self._redact_value(arg) for arg in record.args)
        return True
    
    def _redact(self, text: str) -> str:
        """Apply all redaction patterns to text."""
        for pattern, replacement in self.PATTERNS:
            text = pattern.sub(replacement, text)
        return text
    
    def _redact_value(self, value: Any) -> Any:
        """Redact sensitive values recursively."""
        if isinstance(value, str):
            return self._redact(value)
        if isinstance(value, dict):
            return {k: self._redact_value(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return type(value)(self._redact_value(v) for v in value)
        return value


# ============================================================================
# CUSTOM FORMATTERS
# ============================================================================

class ColoredFormatter(logging.Formatter):
    """
    Color-coded formatter for development console output.
    
    Colors:
    - DEBUG: Cyan
    - INFO: Green
    - WARNING: Yellow
    - ERROR: Red
    - CRITICAL: Red + Bold
    """
    
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[1;31m', # Red + Bold
    }
    RESET = '\033[0m'
    
    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname:<8}{self.RESET}"
        record.name = f"\033[35m{record.name}{self.RESET}"  # Magenta for module
        return super().format(record)


class JSONFormatter(logging.Formatter):
    """
    JSON formatter for production logs (ELK/Datadog/CloudWatch compatible).
    
    Output format:
    {
        "timestamp": "2026-06-03T12:00:00.000Z",
        "level": "INFO",
        "logger": "app.api.auth",
        "message": "Token stored",
        "module": "auth",
        "function": "oauth_callback",
        "line": 123
    }
    """
    
    def format(self, record: logging.LogRecord) -> str:
        import json
        from datetime import datetime, timezone
        
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        for key in ['legacy_id', 'health_id', 'request_id', 'user_id']:
            if hasattr(record, key):
                log_data[key] = getattr(record, key)
        
        return json.dumps(log_data, ensure_ascii=False)


# ============================================================================
# LOGGING SETUP
# ============================================================================

def setup_logging() -> None:
    """
    Configure application-wide logging.
    
    Call this once at application startup (in main.py).
    """
    settings = get_settings()
    
    # Determine log level
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Add sensitive data filter globally
    sensitive_filter = SensitiveDataFilter()
    
    # Determine format based on environment
    use_json = settings.is_production
    
    if use_json:
        # Production: JSON format to file + console
        formatter = JSONFormatter()
        
        # Console handler (JSON)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        console_handler.addFilter(sensitive_filter)
        root_logger.addHandler(console_handler)
        
        # File handler with rotation
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_dir / "app.log",
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=10,
            encoding="utf-8"
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        file_handler.addFilter(sensitive_filter)
        root_logger.addHandler(file_handler)
        
        # Separate error log
        error_handler = logging.handlers.RotatingFileHandler(
            log_dir / "error.log",
            maxBytes=10 * 1024 * 1024,
            backupCount=10,
            encoding="utf-8"
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        error_handler.addFilter(sensitive_filter)
        root_logger.addHandler(error_handler)
    
    else:
        # Development: Colored console output
        console_format = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        formatter = ColoredFormatter(console_format, datefmt="%H:%M:%S")
        
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        console_handler.addFilter(sensitive_filter)
        root_logger.addHandler(console_handler)
    
    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("google_auth_oauthlib").setLevel(logging.WARNING)
    logging.getLogger("oauthlib").setLevel(logging.WARNING)
    logging.getLogger("requests_oauthlib").setLevel(logging.WARNING)
    logging.getLogger("motor").setLevel(logging.WARNING)
    logging.getLogger("pymongo").setLevel(logging.WARNING)
    
    # Log startup info
    logger = logging.getLogger(__name__)
    logger.info(f"📝 Logging configured: level={settings.log_level}, format={'JSON' if use_json else 'colored'}")
    if use_json:
        logger.info(f"📂 Log files: logs/app.log, logs/error.log")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.
    
    Convenience wrapper for consistency across the application.
    
    Usage:
        from app.core.logging import get_logger
        logger = get_logger(__name__)
        logger.info("Something happened")
    """
    return logging.getLogger(name)


# ============================================================================
# CONTEXT-AWARE LOGGING HELPERS
# ============================================================================

class LoggerAdapter(logging.LoggerAdapter):
    """
    Logger adapter that automatically adds context to log messages.
    
    Usage:
        logger = LoggerAdapter(get_logger(__name__), {
            'legacy_id': '123',
            'request_id': 'abc'
        })
        logger.info("Processing token")
        # Output includes legacy_id and request_id in structured logs
    """
    
    def process(self, msg: str, kwargs: dict) -> tuple[str, dict]:
        extra = kwargs.get('extra', {})
        extra.update(self.extra)
        kwargs['extra'] = extra
        return msg, kwargs


def get_context_logger(name: str, **context) -> LoggerAdapter:
    """
    Get a logger with pre-bound context fields.
    
    Usage:
        logger = get_context_logger(__name__, legacy_id="123", request_id="abc")
        logger.info("Processing")  # Automatically includes legacy_id and request_id
    """
    return LoggerAdapter(get_logger(name), context)