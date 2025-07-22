"""Alert system for error monitoring and admin notifications."""

import asyncio
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
from loguru import logger

from core.database import Database


class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning" 
    ERROR = "error"
    CRITICAL = "critical"


class AlertSystem:
    """Comprehensive alert system for monitoring and notifications."""
    
    def __init__(self, database: Database, admin_handler=None):
        self.database = database
        self.admin_handler = admin_handler
        self.alert_history: List[Dict[str, Any]] = []
        self.alert_thresholds = {
            'error_rate_threshold': 0.1,  # 10% error rate triggers alert
            'message_failure_threshold': 5,  # 5 consecutive failures
            'session_offline_threshold': 300,  # 5 minutes offline
            'bot_token_invalid_threshold': 3,  # 3 validation failures
            'memory_usage_threshold': 85,  # 85% memory usage
        }
        self.alert_cooldowns = {
            AlertLevel.INFO: timedelta(minutes=30),
            AlertLevel.WARNING: timedelta(minutes=15),
            AlertLevel.ERROR: timedelta(minutes=5),
            AlertLevel.CRITICAL: timedelta(minutes=1)
        }
        self.last_alerts: Dict[str, datetime] = {}
        self.running = False
    
    async def start(self):
        """Start the alert monitoring system."""
        if self.running:
            return
        
        self.running = True
        logger.info("Alert system started")
        
        # Start monitoring loops
        asyncio.create_task(self._monitor_system_health())
        asyncio.create_task(self._monitor_message_flow())
        asyncio.create_task(self._monitor_session_health())
    
    async def stop(self):
        """Stop the alert system."""
        self.running = False
        logger.info("Alert system stopped")
    
    async def send_alert(self, level: AlertLevel, title: str, message: str, source: str = "system", data: Optional[Dict] = None):
        """Send an alert to administrators."""
        try:
            # Check cooldown
            alert_key = f"{source}:{title}"
            if self._is_in_cooldown(alert_key, level):
                return
            
            # Create alert record
            alert = {
                'timestamp': datetime.now(),
                'level': level.value,
                'title': title,
                'message': message,
                'source': source,
                'data': data or {}
            }
            
            # Add to history
            self.alert_history.append(alert)
            
            # Keep only last 1000 alerts
            if len(self.alert_history) > 1000:
                self.alert_history = self.alert_history[-1000:]
            
            # Update cooldown
            self.last_alerts[alert_key] = datetime.now()
            
            # Format and send to admins
            formatted_message = self._format_alert_message(alert)
            if self.admin_handler:
                await self.admin_handler.broadcast_message(formatted_message)
            
            logger.warning(f"Alert sent: {level.value.upper()} - {title}")
            
        except Exception as e:
            logger.error(f"Failed to send alert: {e}")
    
    def _is_in_cooldown(self, alert_key: str, level: AlertLevel) -> bool:
        """Check if alert is in cooldown period."""
        if alert_key not in self.last_alerts:
            return False
        
        last_alert = self.last_alerts[alert_key]
        cooldown_period = self.alert_cooldowns[level]
        
        return datetime.now() - last_alert < cooldown_period
    
    def _format_alert_message(self, alert: Dict[str, Any]) -> str:
        """Format alert for admin message."""
        level_emoji = {
            'info': 'ℹ️',
            'warning': '⚠️',
            'error': '❌',
            'critical': '🚨'
        }
        
        emoji = level_emoji.get(alert['level'], '📢')
        timestamp = alert['timestamp'].strftime('%H:%M:%S')
        
        message = f"{emoji} **{alert['level'].upper()} ALERT**\n\n"
        message += f"**{alert['title']}**\n"
        message += f"{alert['message']}\n\n"
        message += f"🕒 Time: {timestamp}\n"
        message += f"📍 Source: {alert['source']}"
        
        if alert['data']:
            message += f"\n\n**Details:**\n"
            for key, value in alert['data'].items():
                message += f"• {key}: {value}\n"
        
        return message
    
    # Monitoring methods
    async def _monitor_system_health(self):
        """Monitor overall system health."""
        while self.running:
            try:
                # Check memory usage
                import psutil
                memory_percent = psutil.virtual_memory().percent
                
                if memory_percent > self.alert_thresholds['memory_usage_threshold']:
                    await self.send_alert(
                        AlertLevel.WARNING,
                        "High Memory Usage",
                        f"System memory usage is at {memory_percent:.1f}%",
                        "system",
                        {'memory_percent': memory_percent}
                    )
                
                # Check database connection
                try:
                    pairs = await self.database.get_all_pairs()
                    if pairs is None:
                        await self.send_alert(
                            AlertLevel.ERROR,
                            "Database Connection Failed",
                            "Unable to connect to database",
                            "database"
                        )
                except Exception as e:
                    await self.send_alert(
                        AlertLevel.ERROR,
                        "Database Error",
                        f"Database operation failed: {str(e)}",
                        "database"
                    )
                
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                logger.error(f"Error in system health monitoring: {e}")
                await asyncio.sleep(60)
    
    async def _monitor_message_flow(self):
        """Monitor message forwarding flow."""
        while self.running:
            try:
                # This would track message success/failure rates
                # For now, just a placeholder
                await asyncio.sleep(120)  # Check every 2 minutes
                
            except Exception as e:
                logger.error(f"Error in message flow monitoring: {e}")
                await asyncio.sleep(60)
    
    async def _monitor_session_health(self):
        """Monitor Telegram session health."""
        while self.running:
            try:
                # Check session connectivity
                # This would integrate with session manager
                await asyncio.sleep(180)  # Check every 3 minutes
                
            except Exception as e:
                logger.error(f"Error in session health monitoring: {e}")
                await asyncio.sleep(60)
    
    # Alert management methods
    async def get_recent_alerts(self, limit: int = 50, level: Optional[AlertLevel] = None) -> List[Dict[str, Any]]:
        """Get recent alerts."""
        alerts = self.alert_history[-limit:]
        
        if level:
            alerts = [a for a in alerts if a['level'] == level.value]
        
        return sorted(alerts, key=lambda x: x['timestamp'], reverse=True)
    
    async def clear_alert_history(self, before_date: Optional[datetime] = None):
        """Clear alert history."""
        if before_date:
            self.alert_history = [a for a in self.alert_history if a['timestamp'] > before_date]
        else:
            self.alert_history.clear()
        
        logger.info("Alert history cleared")
    
    async def update_thresholds(self, new_thresholds: Dict[str, Any]):
        """Update alert thresholds."""
        self.alert_thresholds.update(new_thresholds)
        logger.info("Alert thresholds updated")
    
    async def get_alert_stats(self) -> Dict[str, Any]:
        """Get alert statistics."""
        if not self.alert_history:
            return {'total': 0, 'by_level': {}, 'by_source': {}}
        
        by_level = {}
        by_source = {}
        
        for alert in self.alert_history:
            level = alert['level']
            source = alert['source']
            
            by_level[level] = by_level.get(level, 0) + 1
            by_source[source] = by_source.get(source, 0) + 1
        
        return {
            'total': len(self.alert_history),
            'by_level': by_level,
            'by_source': by_source,
            'recent_24h': len([a for a in self.alert_history 
                             if datetime.now() - a['timestamp'] < timedelta(hours=24)])
        }


# Convenience functions for other modules
async def send_error_alert(alert_system: AlertSystem, error: Exception, context: str = ""):
    """Send an error alert."""
    if alert_system:
        await alert_system.send_alert(
            AlertLevel.ERROR,
            f"System Error in {context}",
            f"Error: {str(error)}",
            context,
            {'error_type': type(error).__name__}
        )

async def send_critical_alert(alert_system: AlertSystem, title: str, message: str, context: str = ""):
    """Send a critical alert."""
    if alert_system:
        await alert_system.send_alert(
            AlertLevel.CRITICAL,
            title,
            message,
            context
        )

async def send_warning_alert(alert_system: AlertSystem, title: str, message: str, context: str = ""):
    """Send a warning alert."""
    if alert_system:
        await alert_system.send_alert(
            AlertLevel.WARNING,
            title,
            message,
            context
        )