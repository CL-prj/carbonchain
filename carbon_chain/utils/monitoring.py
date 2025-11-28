"""
CarbonChain - Performance Monitoring
======================================
Metrics collection and performance monitoring.
"""

import time
import functools
from typing import Dict, Callable, Any
from collections import defaultdict
from dataclasses import dataclass, field

from carbon_chain.logging_setup import get_logger

logger = get_logger("utils.monitoring")


# ============================================================================
# METRICS STORAGE
# ============================================================================

@dataclass
class MetricData:
    """
    Performance metric data.
    
    Attributes:
        count: Number of calls
        total_time: Total execution time (seconds)
        min_time: Minimum execution time
        max_time: Maximum execution time
        errors: Number of errors
    """
    count: int = 0
    total_time: float = 0.0
    min_time: float = float('inf')
    max_time: float = 0.0
    errors: int = 0
    
    def update(self, duration: float, error: bool = False):
        """Update metric with new measurement"""
        self.count += 1
        self.total_time += duration
        self.min_time = min(self.min_time, duration)
        self.max_time = max(self.max_time, duration)
        if error:
            self.errors += 1
    
    def get_avg_time(self) -> float:
        """Get average execution time"""
        return self.total_time / self.count if self.count > 0 else 0.0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "count": self.count,
            "total_time_ms": self.total_time * 1000,
            "avg_time_ms": self.get_avg_time() * 1000,
            "min_time_ms": self.min_time * 1000 if self.min_time != float('inf') else 0,
            "max_time_ms": self.max_time * 1000,
            "errors": self.errors,
            "error_rate": self.errors / self.count if self.count > 0 else 0.0
        }


# ============================================================================
# PERFORMANCE MONITOR
# ============================================================================

class PerformanceMonitor:
    """
    Global performance monitor singleton.
    
    Collects and aggregates performance metrics.
    
    Examples:
        >>> monitor = PerformanceMonitor()
        >>> with monitor.measure("my_function"):
        ...     # do work
        ...     pass
        >>> stats = monitor.get_stats()
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._metrics = defaultdict(MetricData)
        return cls._instance
    
    def measure(self, name: str):
        """
        Context manager for measuring execution time.
        
        Args:
            name: Metric name
        
        Examples:
            >>> with monitor.measure("process_block"):
            ...     process_block(block)
        """
        return _MetricContext(self, name)
    
    def record(self, name: str, duration: float, error: bool = False):
        """
        Record metric measurement.
        
        Args:
            name: Metric name
            duration: Duration in seconds
            error: Whether execution resulted in error
        """
        self._metrics[name].update(duration, error)
    
    def get_stats(self, name: Optional[str] = None) -> Dict:
        """
        Get performance statistics.
        
        Args:
            name: Specific metric name (None = all metrics)
        
        Returns:
            Dict: Statistics
        """
        if name:
            return {name: self._metrics[name].to_dict()}
        else:
            return {k: v.to_dict() for k, v in self._metrics.items()}
    
    def reset(self):
        """Reset all metrics"""
        self._metrics.clear()
    
    def print_stats(self):
        """Print statistics to console"""
        stats = self.get_stats()
        
        if not stats:
            print("No metrics recorded")
            return
        
        print("\n" + "="*60)
        print("PERFORMANCE STATISTICS")
        print("="*60)
        
        for name, data in sorted(stats.items()):
            print(f"\n{name}:")
            print(f"  Calls:      {data['count']}")
            print(f"  Avg time:   {data['avg_time_ms']:.2f} ms")
            print(f"  Min time:   {data['min_time_ms']:.2f} ms")
            print(f"  Max time:   {data['max_time_ms']:.2f} ms")
            print(f"  Total time: {data['total_time_ms']:.2f} ms")
            if data['errors'] > 0:
                print(f"  Errors:     {data['errors']} ({data['error_rate']*100:.1f}%)")


class _MetricContext:
    """Context manager for metric measurement"""
    
    def __init__(self, monitor: PerformanceMonitor, name: str):
        self.monitor = monitor
        self.name = name
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        error = exc_type is not None
        self.monitor.record(self.name, duration, error)
        return False


# ============================================================================
# DECORATORS
# ============================================================================

def monitor_performance(name: Optional[str] = None):
    """
    Decorator for monitoring function performance.
    
    Args:
        name: Metric name (default: function name)
    
    Examples:
        >>> @monitor_performance()
        ... def process_transaction(tx):
        ...     # processing logic
        ...     pass
    """
    def decorator(func: Callable) -> Callable:
        metric_name = name or f"{func.__module__}.{func.__name__}"
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            monitor = PerformanceMonitor()
            
            with monitor.measure(metric_name):
                return func(*args, **kwargs)
        
        return wrapper
    return decorator


def monitor_async_performance(name: Optional[str] = None):
    """
    Decorator for monitoring async function performance.
    
    Args:
        name: Metric name
    
    Examples:
        >>> @monitor_async_performance()
        ... async def fetch_data():
        ...     # async logic
        ...     pass
    """
    def decorator(func: Callable) -> Callable:
        metric_name = name or f"{func.__module__}.{func.__name__}"
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            monitor = PerformanceMonitor()
            start_time = time.time()
            error = False
            
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                error = True
                raise
            finally:
                duration = time.time() - start_time
                monitor.record(metric_name, duration, error)
        
        return wrapper
    return decorator


# ============================================================================
# GLOBAL MONITOR INSTANCE
# ============================================================================

def get_metrics() -> Dict:
    """
    Get all collected metrics.
    
    Returns:
        Dict: Performance metrics
    """
    monitor = PerformanceMonitor()
    return monitor.get_stats()


def print_metrics():
    """Print all metrics to console"""
    monitor = PerformanceMonitor()
    monitor.print_stats()


# ============================================================================
# EXPORT
# ============================================================================

__all__ = [
    "MetricData",
    "PerformanceMonitor",
    "monitor_performance",
    "monitor_async_performance",
    "get_metrics",
    "print_metrics",
]
