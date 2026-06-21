"""
Performance monitoring utilities for DQ_PE platform.
Provides timing, memory tracking, and execution profiling.
"""

import time
import logging
from functools import wraps
from datetime import datetime
from typing import Callable, Any, Dict, List

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """Track and report performance metrics."""
    
    def __init__(self):
        self.metrics: Dict[str, List[float]] = {}
        self.start_times: Dict[str, float] = {}
    
    def start_timer(self, name: str) -> None:
        """Start timing a named operation."""
        self.start_times[name] = time.time()
        logger.debug(f"Timer started: {name}")
    
    def end_timer(self, name: str) -> float:
        """End timing and record elapsed time (in seconds)."""
        if name not in self.start_times:
            logger.warning(f"Timer '{name}' was not started")
            return 0.0
        
        elapsed = time.time() - self.start_times.pop(name)
        
        if name not in self.metrics:
            self.metrics[name] = []
        
        self.metrics[name].append(elapsed)
        logger.debug(f"Timer ended: {name} ({elapsed:.3f}s)")
        
        return elapsed
    
    def get_stats(self, name: str) -> Dict[str, float]:
        """Get statistics for a named operation."""
        if name not in self.metrics or not self.metrics[name]:
            return {}
        
        times = self.metrics[name]
        return {
            "count": len(times),
            "total": sum(times),
            "min": min(times),
            "max": max(times),
            "avg": sum(times) / len(times)
        }
    
    def report(self) -> str:
        """Generate performance report."""
        if not self.metrics:
            return "No performance metrics recorded."
        
        lines = [
            "="*70,
            "Performance Report",
            "="*70
        ]
        
        for name in sorted(self.metrics.keys()):
            stats = self.get_stats(name)
            lines.append(
                f"{name:40} | "
                f"Calls: {stats['count']:3d} | "
                f"Total: {stats['total']:7.2f}s | "
                f"Avg: {stats['avg']:6.2f}s"
            )
        
        lines.append("="*70)
        return "\n".join(lines)


# Global performance monitor instance
_global_monitor = PerformanceMonitor()


def timed_operation(operation_name: str) -> Callable:
    """
    Decorator to automatically time function execution.
    
    Args:
        operation_name: Name for the timed operation
    
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            _global_monitor.start_timer(operation_name)
            try:
                return func(*args, **kwargs)
            finally:
                elapsed = _global_monitor.end_timer(operation_name)
                logger.info(f"{operation_name} completed in {elapsed:.3f}s")
        
        return wrapper
    
    return decorator


def get_performance_report() -> str:
    """Get global performance report."""
    return _global_monitor.report()


def reset_performance_metrics() -> None:
    """Reset all performance metrics."""
    _global_monitor.metrics.clear()
    _global_monitor.start_times.clear()


class ExecutionTimer:
    """Context manager for timing code blocks."""
    
    def __init__(self, name: str):
        self.name = name
        self.start_time = None
    
    def __enter__(self) -> 'ExecutionTimer':
        self.start_time = time.time()
        logger.debug(f"Execution timer started: {self.name}")
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        elapsed = time.time() - self.start_time
        logger.info(f"{self.name} took {elapsed:.3f}s")
    
    @property
    def elapsed(self) -> float:
        """Get elapsed time in seconds."""
        if self.start_time is None:
            return 0.0
        return time.time() - self.start_time
