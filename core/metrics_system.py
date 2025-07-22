"""Prometheus-style metrics system for comprehensive bot monitoring."""

import asyncio
import time
import psutil
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict, deque
from loguru import logger

from core.database import Database


@dataclass
class MetricPoint:
    """Single metric data point."""
    timestamp: float
    value: float
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class MetricSeries:
    """Time series of metric points."""
    name: str
    help: str
    metric_type: str  # counter, gauge, histogram, summary
    points: deque = field(default_factory=lambda: deque(maxlen=1000))
    
    def add_point(self, value: float, labels: Optional[Dict[str, str]] = None):
        """Add a metric point."""
        self.points.append(MetricPoint(
            timestamp=time.time(),
            value=value,
            labels=labels or {}
        ))


class MetricsCollector:
    """Comprehensive metrics collection system."""
    
    def __init__(self, database: Database):
        self.database = database
        self.metrics: Dict[str, MetricSeries] = {}
        self.counters: Dict[str, float] = defaultdict(float)
        self.gauges: Dict[str, float] = defaultdict(float)
        self.histograms: Dict[str, List[float]] = defaultdict(list)
        
        # System monitoring
        self.process = psutil.Process()
        self.running = False
        
        # Initialize core metrics
        self._initialize_metrics()
    
    def _initialize_metrics(self):
        """Initialize core bot metrics."""
        # Message flow metrics
        self._register_metric("messages_processed_total", "Total messages processed", "counter")
        self._register_metric("messages_forwarded_total", "Total messages forwarded", "counter")
        self._register_metric("messages_filtered_total", "Total messages filtered", "counter")
        self._register_metric("message_processing_duration_seconds", "Message processing duration", "histogram")
        
        # Error metrics
        self._register_metric("errors_total", "Total errors by type", "counter")
        self._register_metric("api_errors_total", "API errors by service", "counter")
        self._register_metric("session_errors_total", "Session-related errors", "counter")
        
        # Session metrics
        self._register_metric("active_sessions_count", "Number of active sessions", "gauge")
        self._register_metric("session_health_checks_total", "Session health checks performed", "counter")
        self._register_metric("session_failures_total", "Session failure events", "counter")
        
        # Performance metrics
        self._register_metric("memory_usage_bytes", "Memory usage in bytes", "gauge")
        self._register_metric("cpu_usage_percent", "CPU usage percentage", "gauge")
        self._register_metric("active_pairs_count", "Number of active forwarding pairs", "gauge")
        self._register_metric("worker_groups_count", "Number of worker groups", "gauge")
        
        # API rate limiting metrics
        self._register_metric("api_requests_total", "Total API requests by service", "counter")
        self._register_metric("api_rate_limit_hits_total", "API rate limit violations", "counter")
        self._register_metric("api_response_time_seconds", "API response times", "histogram")
        
        logger.info("Core metrics initialized")
    
    def _register_metric(self, name: str, help: str, metric_type: str):
        """Register a new metric."""
        self.metrics[name] = MetricSeries(name=name, help=help, metric_type=metric_type)
    
    async def start_collection(self):
        """Start metrics collection."""
        if self.running:
            return
        
        self.running = True
        logger.info("Starting metrics collection")
        
        # Start background collection tasks
        asyncio.create_task(self._collect_system_metrics())
        asyncio.create_task(self._collect_database_metrics())
    
    async def stop_collection(self):
        """Stop metrics collection."""
        self.running = False
        logger.info("Metrics collection stopped")
    
    # Counter operations
    def increment_counter(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None):
        """Increment a counter metric."""
        self.counters[name] += value
        if name in self.metrics:
            self.metrics[name].add_point(self.counters[name], labels)
    
    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Set a gauge metric value."""
        self.gauges[name] = value
        if name in self.metrics:
            self.metrics[name].add_point(value, labels)
    
    def observe_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Add observation to histogram."""
        self.histograms[name].append(value)
        if name in self.metrics:
            self.metrics[name].add_point(value, labels)
    
    # High-level metric recording methods
    def record_message_processed(self, pair_id: int, processing_time: float):
        """Record message processing metrics."""
        self.increment_counter("messages_processed_total", labels={"pair_id": str(pair_id)})
        self.observe_histogram("message_processing_duration_seconds", processing_time)
    
    def record_message_forwarded(self, pair_id: int, source_platform: str, dest_platform: str):
        """Record message forwarding."""
        self.increment_counter("messages_forwarded_total", labels={
            "pair_id": str(pair_id),
            "source": source_platform,
            "destination": dest_platform
        })
    
    def record_message_filtered(self, pair_id: int, filter_reason: str):
        """Record message filtering."""
        self.increment_counter("messages_filtered_total", labels={
            "pair_id": str(pair_id),
            "reason": filter_reason
        })
    
    def record_error(self, error_type: str, source: str, severity: str):
        """Record error occurrence."""
        self.increment_counter("errors_total", labels={
            "type": error_type,
            "source": source,
            "severity": severity
        })
    
    def record_api_request(self, service: str, method: str, status_code: int, duration: float):
        """Record API request metrics."""
        self.increment_counter("api_requests_total", labels={
            "service": service,
            "method": method,
            "status": str(status_code)
        })
        self.observe_histogram("api_response_time_seconds", duration, labels={
            "service": service,
            "method": method
        })
    
    def record_session_health_check(self, session_name: str, is_healthy: bool):
        """Record session health check."""
        self.increment_counter("session_health_checks_total", labels={
            "session": session_name,
            "result": "healthy" if is_healthy else "unhealthy"
        })
        
        if not is_healthy:
            self.increment_counter("session_failures_total", labels={
                "session": session_name
            })
    
    async def _collect_system_metrics(self):
        """Collect system performance metrics."""
        while self.running:
            try:
                # Memory usage
                memory_info = self.process.memory_info()
                self.set_gauge("memory_usage_bytes", memory_info.rss)
                
                # CPU usage
                cpu_percent = self.process.cpu_percent()
                self.set_gauge("cpu_usage_percent", cpu_percent)
                
                # Collect database metrics
                session_count = await self.database.get_session_count()
                self.set_gauge("active_sessions_count", session_count)
                
                pair_count = await self.database.get_active_pairs_count()
                self.set_gauge("active_pairs_count", pair_count)
                
                await asyncio.sleep(30)  # Collect every 30 seconds
                
            except Exception as e:
                logger.error(f"Error collecting system metrics: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _collect_database_metrics(self):
        """Collect database-related metrics."""
        while self.running:
            try:
                # Database connection pool metrics if available
                # This would depend on your database setup
                
                await asyncio.sleep(60)  # Collect every minute
                
            except Exception as e:
                logger.error(f"Error collecting database metrics: {e}")
                await asyncio.sleep(120)
    
    def get_metric_summary(self, name: str, time_window: Optional[int] = None) -> Dict[str, Any]:
        """Get summary statistics for a metric."""
        if name not in self.metrics:
            return {}
        
        metric = self.metrics[name]
        now = time.time()
        
        # Filter points by time window if specified
        if time_window:
            cutoff = now - time_window
            points = [p for p in metric.points if p.timestamp >= cutoff]
        else:
            points = list(metric.points)
        
        if not points:
            return {"name": name, "points": 0}
        
        values = [p.value for p in points]
        
        summary = {
            "name": name,
            "type": metric.metric_type,
            "points": len(points),
            "latest_value": values[-1] if values else 0,
            "time_range": {
                "start": min(p.timestamp for p in points),
                "end": max(p.timestamp for p in points)
            }
        }
        
        if metric.metric_type in ["gauge", "histogram"]:
            summary.update({
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values),
                "sum": sum(values)
            })
        
        return summary
    
    def get_health_metrics(self) -> Dict[str, Any]:
        """Get comprehensive health metrics for monitoring dashboard."""
        try:
            current_time = time.time()
            last_hour = current_time - 3600
            
            return {
                "timestamp": current_time,
                "system": {
                    "memory_usage_mb": self.gauges.get("memory_usage_bytes", 0) / 1024 / 1024,
                    "cpu_usage_percent": self.gauges.get("cpu_usage_percent", 0),
                    "uptime_seconds": current_time - getattr(self, 'start_time', current_time)
                },
                "messages": {
                    "processed_total": self.counters.get("messages_processed_total", 0),
                    "forwarded_total": self.counters.get("messages_forwarded_total", 0),
                    "filtered_total": self.counters.get("messages_filtered_total", 0),
                    "success_rate": self._calculate_success_rate()
                },
                "sessions": {
                    "active_count": self.gauges.get("active_sessions_count", 0),
                    "health_checks_total": self.counters.get("session_health_checks_total", 0),
                    "failures_total": self.counters.get("session_failures_total", 0)
                },
                "errors": {
                    "total": self.counters.get("errors_total", 0),
                    "api_errors": self.counters.get("api_errors_total", 0),
                    "session_errors": self.counters.get("session_errors_total", 0)
                },
                "performance": {
                    "avg_processing_time": self._calculate_avg_processing_time(),
                    "api_avg_response_time": self._calculate_avg_api_response_time(),
                    "active_pairs": self.gauges.get("active_pairs_count", 0)
                }
            }
        except Exception as e:
            logger.error(f"Error generating health metrics: {e}")
            return {}
    
    def _calculate_success_rate(self) -> float:
        """Calculate message forwarding success rate."""
        processed = self.counters.get("messages_processed_total", 0)
        forwarded = self.counters.get("messages_forwarded_total", 0)
        
        if processed == 0:
            return 1.0
        
        return forwarded / processed
    
    def _calculate_avg_processing_time(self) -> float:
        """Calculate average message processing time."""
        times = self.histograms.get("message_processing_duration_seconds", [])
        if not times:
            return 0.0
        
        return sum(times) / len(times)
    
    def _calculate_avg_api_response_time(self) -> float:
        """Calculate average API response time."""
        times = self.histograms.get("api_response_time_seconds", [])
        if not times:
            return 0.0
        
        return sum(times) / len(times)
    
    def export_prometheus_format(self) -> str:
        """Export metrics in Prometheus format."""
        lines = []
        
        for name, metric in self.metrics.items():
            if not metric.points:
                continue
            
            # Add help comment
            lines.append(f"# HELP {name} {metric.help}")
            lines.append(f"# TYPE {name} {metric.metric_type}")
            
            # Add latest point
            latest_point = metric.points[-1]
            labels_str = ""
            if latest_point.labels:
                label_pairs = [f'{k}="{v}"' for k, v in latest_point.labels.items()]
                labels_str = "{" + ",".join(label_pairs) + "}"
            
            lines.append(f"{name}{labels_str} {latest_point.value}")
        
        return "\n".join(lines)


# Global metrics collector instance
metrics_collector: Optional[MetricsCollector] = None


def init_metrics_collector(database: Database):
    """Initialize global metrics collector."""
    global metrics_collector
    metrics_collector = MetricsCollector(database)
    metrics_collector.start_time = time.time()
    logger.info("Metrics collector initialized")


def get_metrics_collector() -> Optional[MetricsCollector]:
    """Get the global metrics collector instance."""
    return metrics_collector


# Convenience functions for metric recording
def record_message_processed(pair_id: int, processing_time: float):
    """Record message processing (convenience function)."""
    if metrics_collector:
        metrics_collector.record_message_processed(pair_id, processing_time)


def record_error(error_type: str, source: str, severity: str = "medium"):
    """Record error (convenience function)."""
    if metrics_collector:
        metrics_collector.record_error(error_type, source, severity)


def record_api_request(service: str, method: str, status_code: int, duration: float):
    """Record API request (convenience function)."""
    if metrics_collector:
        metrics_collector.record_api_request(service, method, status_code, duration)