"""Unified error handling middleware for comprehensive error capture and reporting."""

import asyncio
import traceback
import sys
from typing import Any, Callable, Optional, Dict, List
from datetime import datetime
from functools import wraps
from dataclasses import dataclass, asdict
from loguru import logger

from core.database import Database


@dataclass
class ErrorContext:
    """Context information for error tracking."""
    function_name: str
    module_name: str
    pair_id: Optional[int] = None
    session_name: Optional[str] = None
    user_id: Optional[int] = None
    operation_type: Optional[str] = None
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


@dataclass
class ErrorReport:
    """Comprehensive error report structure."""
    error_id: str
    error_type: str
    error_message: str
    traceback_info: str
    context: ErrorContext
    severity: str
    timestamp: datetime
    resolved: bool = False
    admin_notified: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error report to dictionary."""
        return {
            'error_id': self.error_id,
            'error_type': self.error_type,
            'error_message': self.error_message,
            'traceback_info': self.traceback_info,
            'context': asdict(self.context),
            'severity': self.severity,
            'timestamp': self.timestamp.isoformat(),
            'resolved': self.resolved,
            'admin_notified': self.admin_notified
        }


class ErrorMiddleware:
    """Unified error handling middleware with automatic reporting."""
    
    def __init__(self, database: Database, admin_handler=None):
        self.database = database
        self.admin_handler = admin_handler
        self.error_history: List[ErrorReport] = []
        self.error_counts: Dict[str, int] = {}
        self.critical_error_threshold = 5
        self.admin_notification_enabled = True
        
        # Error severity mapping
        self.severity_mapping = {
            'ConnectionError': 'high',
            'TimeoutError': 'medium',
            'AuthenticationError': 'critical',
            'ValidationError': 'low',
            'SessionError': 'high',
            'DatabaseError': 'critical',
            'APIError': 'medium'
        }
    
    def capture_async(self, context: Optional[ErrorContext] = None):
        """Decorator for async functions with comprehensive error capture."""
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                error_context = context or ErrorContext(
                    function_name=func.__name__,
                    module_name=func.__module__
                )
                
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    await self._handle_error(e, error_context)
                    raise
            return wrapper
        return decorator
    
    def capture_sync(self, context: Optional[ErrorContext] = None):
        """Decorator for sync functions with comprehensive error capture."""
        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                error_context = context or ErrorContext(
                    function_name=func.__name__,
                    module_name=func.__module__
                )
                
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    asyncio.create_task(self._handle_error(e, error_context))
                    raise
            return wrapper
        return decorator
    
    async def _handle_error(self, error: Exception, context: ErrorContext):
        """Handle and process errors with reporting."""
        try:
            # Generate unique error ID
            error_id = f"{context.function_name}_{int(datetime.utcnow().timestamp())}"
            
            # Determine severity
            error_type = type(error).__name__
            severity = self.severity_mapping.get(error_type, 'medium')
            
            # Create error report
            error_report = ErrorReport(
                error_id=error_id,
                error_type=error_type,
                error_message=str(error),
                traceback_info=traceback.format_exc(),
                context=context,
                severity=severity,
                timestamp=datetime.utcnow()
            )
            
            # Store error report
            self.error_history.append(error_report)
            
            # Update error counts
            self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
            
            # Log with appropriate level
            log_message = f"Error in {context.function_name}: {error}"
            if severity == 'critical':
                logger.critical(log_message, extra={'error_report': error_report.to_dict()})
            elif severity == 'high':
                logger.error(log_message, extra={'error_report': error_report.to_dict()})
            elif severity == 'medium':
                logger.warning(log_message, extra={'error_report': error_report.to_dict()})
            else:
                logger.info(log_message, extra={'error_report': error_report.to_dict()})
            
            # Notify admin for critical errors
            if severity in ['critical', 'high'] and self.admin_notification_enabled:
                await self._notify_admin(error_report)
            
            # Check for error patterns
            await self._analyze_error_patterns()
            
        except Exception as handler_error:
            logger.critical(f"Error in error handler: {handler_error}")
    
    async def _notify_admin(self, error_report: ErrorReport):
        """Notify administrators about critical errors."""
        try:
            if not self.admin_handler:
                return
            
            message = f"🚨 **Critical Error Detected**\n\n"
            message += f"**Error ID:** `{error_report.error_id}`\n"
            message += f"**Type:** {error_report.error_type}\n"
            message += f"**Function:** {error_report.context.function_name}\n"
            message += f"**Message:** {error_report.error_message}\n"
            message += f"**Time:** {error_report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
            
            if error_report.context.pair_id:
                message += f"**Pair ID:** {error_report.context.pair_id}\n"
            if error_report.context.session_name:
                message += f"**Session:** {error_report.context.session_name}\n"
            
            await self.admin_handler.send_admin_notification(message, priority='high')
            error_report.admin_notified = True
            
        except Exception as e:
            logger.error(f"Failed to notify admin about error: {e}")
    
    async def _analyze_error_patterns(self):
        """Analyze error patterns and detect critical trends."""
        try:
            # Check for repeated errors
            recent_errors = [e for e in self.error_history 
                           if (datetime.utcnow() - e.timestamp).seconds < 300]  # Last 5 minutes
            
            if len(recent_errors) >= self.critical_error_threshold:
                logger.critical(f"High error rate detected: {len(recent_errors)} errors in 5 minutes")
                
                if self.admin_handler:
                    await self.admin_handler.send_admin_notification(
                        f"⚠️ **High Error Rate Alert**\n\n"
                        f"Detected {len(recent_errors)} errors in the last 5 minutes.\n"
                        f"Please investigate immediately.",
                        priority='critical'
                    )
            
            # Clean old error history (keep last 1000 errors)
            if len(self.error_history) > 1000:
                self.error_history = self.error_history[-1000:]
                
        except Exception as e:
            logger.error(f"Error in pattern analysis: {e}")
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get comprehensive error statistics."""
        try:
            total_errors = len(self.error_history)
            recent_errors = [e for e in self.error_history 
                           if (datetime.utcnow() - e.timestamp).total_seconds() < 86400]
            
            return {
                'total_errors': total_errors,
                'errors_24h': len(recent_errors),
                'error_types': dict(self.error_counts),
                'critical_errors': len([e for e in recent_errors if e.severity == 'critical']),
                'high_errors': len([e for e in recent_errors if e.severity == 'high']),
                'error_rate_24h': len(recent_errors) / 24 if recent_errors else 0,
                'most_common_error': max(self.error_counts.items(), key=lambda x: x[1])[0] if self.error_counts else None
            }
        except Exception as e:
            logger.error(f"Error generating statistics: {e}")
            return {}
    
    async def mark_error_resolved(self, error_id: str) -> bool:
        """Mark an error as resolved."""
        try:
            for error_report in self.error_history:
                if error_report.error_id == error_id:
                    error_report.resolved = True
                    logger.info(f"Marked error {error_id} as resolved")
                    return True
            return False
        except Exception as e:
            logger.error(f"Error marking error as resolved: {e}")
            return False


# Global error middleware instance (initialized by main application)
error_middleware: Optional[ErrorMiddleware] = None


def init_error_middleware(database: Database, admin_handler=None):
    """Initialize global error middleware."""
    global error_middleware
    error_middleware = ErrorMiddleware(database, admin_handler)
    logger.info("Error middleware initialized")


def get_error_middleware() -> Optional[ErrorMiddleware]:
    """Get the global error middleware instance."""
    return error_middleware


# Convenience decorators
def handle_errors_async(context: Optional[ErrorContext] = None):
    """Convenience decorator for async error handling."""
    def decorator(func):
        if error_middleware:
            return error_middleware.capture_async(context)(func)
        return func
    return decorator


def handle_errors_sync(context: Optional[ErrorContext] = None):
    """Convenience decorator for sync error handling."""
    def decorator(func):
        if error_middleware:
            return error_middleware.capture_sync(context)(func)
        return func
    return decorator