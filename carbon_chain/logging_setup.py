"""
CarbonChain - Logging System
==============================
Sistema logging strutturato JSON per audit e debugging.

Security Level: HIGH
Last Updated: 2025-11-26
Version: 1.0.0

Features:
- Logging JSON strutturato
- Rotation automatica
- Multiple handlers (file, console, syslog)
- Context enrichment
- Performance tracking
- Audit trail
"""

import logging
import logging.handlers
import json
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import traceback


# ============================================================================
# JSON FORMATTER
# ============================================================================

class JSONFormatter(logging.Formatter):
    """
    Formatter per log in formato JSON.
    
    Output structure:
    {
        "timestamp": "2025-11-26T22:00:00.000Z",
        "level": "INFO",
        "logger": "blockchain",
        "message": "Block added",
        "node_id": "abc123",
        "extra_data": {...},
        "exception": {...}
    }
    """
    
    def __init__(
        self,
        include_extra: bool = True,
        include_stack: bool = True
    ):
        super().__init__()
        self.include_extra = include_extra
        self.include_stack = include_stack
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Formatta LogRecord in JSON.
        
        Args:
            record: LogRecord da formattare
        
        Returns:
            str: JSON string
        """
        # Base fields
        log_data = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Thread info
        if record.thread:
            log_data["thread_id"] = record.thread
            log_data["thread_name"] = record.threadName
        
        # Process info
        if record.process:
            log_data["process_id"] = record.process
        
        # Extra data (custom fields)
        if self.include_extra and hasattr(record, 'extra_data'):
            log_data["extra_data"] = record.extra_data
        
        # Exception info
        if record.exc_info and self.include_stack:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }
        
        return json.dumps(log_data, default=str)


# ============================================================================
# TEXT FORMATTER (Human-Readable)
# ============================================================================

class ColoredTextFormatter(logging.Formatter):
    """
    Formatter colorato per console.
    
    Colors:
    - DEBUG: Gray
    - INFO: Green
    - WARNING: Yellow
    - ERROR: Red
    - CRITICAL: Bold Red
    """
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[90m',      # Gray
        'INFO': '\033[92m',       # Green
        'WARNING': '\033[93m',    # Yellow
        'ERROR': '\033[91m',      # Red
        'CRITICAL': '\033[1;91m', # Bold Red
        'RESET': '\033[0m'        # Reset
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """Formatta con colori"""
        # Add color
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = (
                f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"
            )
        
        # Format timestamp
        timestamp = datetime.utcfromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        
        # Build message
        message = f"{timestamp} [{record.levelname}] {record.name}: {record.getMessage()}"
        
        # Add extra data if present
        if hasattr(record, 'extra_data'):
            message += f" | {record.extra_data}"
        
        # Add exception
        if record.exc_info:
            message += f"\n{self.formatException(record.exc_info)}"
        
        return message


# ============================================================================
# LOGGER CLASS
# ============================================================================

class CarbonChainLogger:
    """
    Wrapper logger con features avanzate.
    
    Features:
    - Context enrichment
    - Performance tracking
    - Structured logging
    """
    
    def __init__(self, logger: logging.Logger):
        self._logger = logger
        self._context: Dict[str, Any] = {}
    
    def set_context(self, **kwargs):
        """
        Imposta context globale (aggiunto a tutti i log).
        
        Example:
            >>> logger.set_context(node_id="abc123", network="mainnet")
        """
        self._context.update(kwargs)
    
    def clear_context(self):
        """Clear context"""
        self._context.clear()
    
    def _log(
        self,
        level: int,
        message: str,
        extra_data: Optional[Dict[str, Any]] = None,
        exc_info: Optional[Exception] = None
    ):
        """Internal log method"""
        # Merge context + extra_data
        merged_extra = {**self._context}
        if extra_data:
            merged_extra.update(extra_data)
        
        # Create LogRecord with extra
        self._logger.log(
            level,
            message,
            exc_info=exc_info,
            extra={'extra_data': merged_extra} if merged_extra else {}
        )
    
    def debug(self, message: str, extra_data: Optional[Dict] = None):
        """Log DEBUG"""
        self._log(logging.DEBUG, message, extra_data)
    
    def info(self, message: str, extra_data: Optional[Dict] = None):
        """Log INFO"""
        self._log(logging.INFO, message, extra_data)
    
    def warning(self, message: str, extra_data: Optional[Dict] = None):
        """Log WARNING"""
        self._log(logging.WARNING, message, extra_data)
    
    def error(self, message: str, extra_data: Optional[Dict] = None, exc_info: Optional[Exception] = None):
        """Log ERROR"""
        self._log(logging.ERROR, message, extra_data, exc_info)
    
    def critical(self, message: str, extra_data: Optional[Dict] = None, exc_info: Optional[Exception] = None):
        """Log CRITICAL"""
        self._log(logging.CRITICAL, message, extra_data, exc_info)
    
    def exception(self, message: str, extra_data: Optional[Dict] = None):
        """Log exception con traceback"""
        self._log(logging.ERROR, message, extra_data, exc_info=sys.exc_info())


# ============================================================================
# SETUP FUNCTION
# ============================================================================

def setup_logging(
    log_level: str = "INFO",
    log_to_file: bool = True,
    log_dir: Path = Path("./logs"),
    log_format: str = "json",
    log_rotation_mb: int = 100,
    log_retention_days: int = 30,
    enable_console: bool = True,
) -> CarbonChainLogger:
    """
    Setup logging system completo.
    
    Args:
        log_level: Level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Salva su file
        log_dir: Directory log files
        log_format: Formato (json, text)
        log_rotation_mb: MB prima rotation
        log_retention_days: Giorni retention
        enable_console: Log anche su console
    
    Returns:
        CarbonChainLogger: Logger configurato
    
    Example:
        >>> logger = setup_logging(
        ...     log_level="DEBUG",
        ...     log_format="json",
        ...     log_to_file=True
        ... )
        >>> logger.info("Node started", extra_data={"port": 9000})
    """
    # Create root logger
    root_logger = logging.getLogger("carbonchain")
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # ========================================================================
    # FILE HANDLER (with rotation)
    # ========================================================================
    
    if log_to_file:
        log_dir.mkdir(parents=True, exist_ok=True)
        
        log_file = log_dir / f"carbonchain.log"
        
        # Rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_file,
            maxBytes=log_rotation_mb * 1024 * 1024,  # MB to bytes
            backupCount=log_retention_days,
            encoding='utf-8'
        )
        
        # Set formatter
        if log_format == "json":
            file_handler.setFormatter(JSONFormatter())
        else:
            file_handler.setFormatter(
                logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
            )
        
        root_logger.addHandler(file_handler)
    
    # ========================================================================
    # CONSOLE HANDLER
    # ========================================================================
    
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        
        # Use colored formatter for console
        console_handler.setFormatter(ColoredTextFormatter())
        
        root_logger.addHandler(console_handler)
    
    # ========================================================================
    # ERROR FILE HANDLER (separate error log)
    # ========================================================================
    
    if log_to_file:
        error_file = log_dir / "carbonchain_errors.log"
        
        error_handler = logging.handlers.RotatingFileHandler(
            filename=error_file,
            maxBytes=log_rotation_mb * 1024 * 1024,
            backupCount=log_retention_days,
            encoding='utf-8'
        )
        
        error_handler.setLevel(logging.ERROR)
        
        if log_format == "json":
            error_handler.setFormatter(JSONFormatter(include_stack=True))
        else:
            error_handler.setFormatter(
                logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s\n%(exc_info)s'
                )
            )
        
        root_logger.addHandler(error_handler)
    
    # Wrap in CarbonChainLogger
    return CarbonChainLogger(root_logger)


# ============================================================================
# CATEGORY LOGGERS
# ============================================================================

def get_logger(category: str) -> CarbonChainLogger:
    """
    Ottieni logger per categoria specifica.
    
    Args:
        category: Categoria (blockchain, mining, p2p, api, etc.)
    
    Returns:
        CarbonChainLogger: Logger per categoria
    
    Example:
        >>> mining_logger = get_logger("mining")
        >>> mining_logger.info("Mining started")
    """
    logger = logging.getLogger(f"carbonchain.{category}")
    return CarbonChainLogger(logger)


# ============================================================================
# PERFORMANCE TRACKING
# ============================================================================

class PerformanceLogger:
    """
    Context manager per tracking performance.
    
    Example:
        >>> logger = get_logger("blockchain")
        >>> with PerformanceLogger(logger, "validate_block"):
        ...     # Code to measure
        ...     validate_block(block)
        # Logs: "validate_block completed in 0.123s"
    """
    
    def __init__(
        self,
        logger: CarbonChainLogger,
        operation: str,
        threshold_ms: Optional[int] = None
    ):
        self.logger = logger
        self.operation = operation
        self.threshold_ms = threshold_ms
        self.start_time = None
    
    def __enter__(self):
        import time
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        import time
        elapsed = time.perf_counter() - self.start_time
        elapsed_ms = elapsed * 1000
        
        # Log performance
        extra = {
            "operation": self.operation,
            "duration_ms": round(elapsed_ms, 2)
        }
        
        if self.threshold_ms and elapsed_ms > self.threshold_ms:
            self.logger.warning(
                f"{self.operation} took {elapsed_ms:.2f}ms (threshold: {self.threshold_ms}ms)",
                extra_data=extra
            )
        else:
            self.logger.debug(
                f"{self.operation} completed in {elapsed_ms:.2f}ms",
                extra_data=extra
            )


# ============================================================================
# AUDIT LOGGER
# ============================================================================

class AuditLogger:
    """
    Logger specializzato per audit trail.
    
    Use for:
    - Certificate creations
    - Compensations
    - Block additions
    - Critical operations
    """
    
    def __init__(self, log_dir: Path = Path("./logs")):
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Separate audit log
        audit_file = log_dir / "audit.log"
        
        self.logger = logging.getLogger("carbonchain.audit")
        self.logger.setLevel(logging.INFO)
        
        # File handler (no rotation per audit - keep all)
        handler = logging.FileHandler(audit_file, encoding='utf-8')
        handler.setFormatter(JSONFormatter(include_extra=True))
        
        self.logger.addHandler(handler)
    
    def log_certificate_creation(
        self,
        cert_id: str,
        total_kg: int,
        issuer: str,
        txid: str
    ):
        """Log certificate creation"""
        self.logger.info(
            "Certificate created",
            extra={
                'extra_data': {
                    "action": "certificate_created",
                    "certificate_id": cert_id,
                    "total_kg": total_kg,
                    "issuer": issuer,
                    "txid": txid,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )
    
    def log_compensation(
        self,
        project_id: str,
        amount_kg: int,
        cert_id: str,
        txid: str
    ):
        """Log compensation"""
        self.logger.info(
            "Compensation executed",
            extra={
                'extra_data': {
                    "action": "compensation",
                    "project_id": project_id,
                    "amount_kg": amount_kg,
                    "certificate_id": cert_id,
                    "txid": txid,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )
    
    def log_block_added(self, height: int, block_hash: str, tx_count: int):
        """Log block addition"""
        self.logger.info(
            "Block added",
            extra={
                'extra_data': {
                    "action": "block_added",
                    "height": height,
                    "hash": block_hash,
                    "tx_count": tx_count,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
        )


# ============================================================================
# GLOBAL LOGGER INSTANCE
# ============================================================================

# Default logger (lazy-loaded)
LOGGER: Optional[CarbonChainLogger] = None


def get_default_logger() -> CarbonChainLogger:
    """Get default logger instance"""
    global LOGGER
    
    if LOGGER is None:
        LOGGER = setup_logging()
    
    return LOGGER


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    "setup_logging",
    "get_logger",
    "get_default_logger",
    "CarbonChainLogger",
    "PerformanceLogger",
    "AuditLogger",
    "JSONFormatter",
    "ColoredTextFormatter",
]
