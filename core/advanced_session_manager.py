"""Advanced session manager with multi-session support and worker segregation."""

import asyncio
import os
import json
import uuid
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from loguru import logger
from cryptography.fernet import Fernet

from core.database import Database, SessionInfo, ForwardingPair
from core.session_manager import SessionManager


@dataclass
class WorkerGroup:
    """Worker group for session segregation."""
    worker_id: str
    session_name: str
    pair_ids: List[int]
    max_pairs: int = 30
    is_active: bool = True
    created_at: datetime = None
    last_health_check: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


@dataclass
class SessionHealthCheck:
    """Session health check result."""
    session_name: str
    is_healthy: bool
    status: str
    last_verified: datetime
    error_message: Optional[str] = None
    pair_access_status: Dict[int, bool] = None
    
    def __post_init__(self):
        if self.pair_access_status is None:
            self.pair_access_status = {}


class AdvancedSessionManager:
    """Advanced session manager with multi-session support, worker segregation, and health monitoring."""
    
    def __init__(self, database: Database, base_session_manager: SessionManager):
        self.database = database
        self.base_session_manager = base_session_manager
        self.worker_groups: Dict[str, WorkerGroup] = {}
        self.session_health_cache: Dict[str, SessionHealthCheck] = {}
        self.running = False
        
        # Configuration
        self.max_pairs_per_session = 30
        self.health_check_interval = 300  # 5 minutes
        self.session_timeout = 3600  # 1 hour for expired sessions
        
    async def start(self):
        """Start the advanced session manager."""
        if self.running:
            logger.warning("Advanced session manager is already running")
            return
        
        logger.info("Starting advanced session manager...")
        self.running = True
        
        try:
            # Initialize session data from database
            await self._initialize_sessions()
            
            # Start background tasks
            await asyncio.gather(
                self._health_monitor_loop(),
                self._cleanup_loop(),
                self._worker_manager_loop(),
                return_exceptions=True
            )
            
        except Exception as e:
            logger.error(f"Failed to start advanced session manager: {e}")
            self.running = False
            raise
    
    async def stop(self):
        """Stop the advanced session manager."""
        if not self.running:
            return
        
        logger.info("Stopping advanced session manager...")
        self.running = False
        
        # Stop all worker groups
        for worker_id, worker_group in self.worker_groups.items():
            worker_group.is_active = False
            logger.debug(f"Stopped worker group: {worker_id}")
        
        logger.info("Advanced session manager stopped")
    
    async def register_session(self, session_name: str, phone_number: str, priority: int = 1, max_pairs: int = 30) -> bool:
        """Register a new session with enhanced metadata."""
        try:
            # Check if session already exists
            existing_session = await self.database.get_session_info(session_name)
            if existing_session:
                logger.warning(f"Session {session_name} already exists")
                return False
            
            # Create session info
            session_info = SessionInfo(
                name=session_name,
                phone_number=phone_number,
                is_active=False,
                health_status="registered",
                pair_count=0,
                max_pairs=max_pairs,
                priority=priority,
                metadata_info={
                    "registration_time": datetime.utcnow().isoformat(),
                    "auto_created": False,
                    "registration_source": "manual",
                    "authentication_pending": True
                }
            )
            
            # Add to database
            session_id = await self.database.add_session_info(session_info)
            session_info.id = session_id
            
            # Create session structure in base session manager
            await self.base_session_manager.create_session(session_name, phone_number)
            
            logger.info(f"Successfully registered session: {session_name} (ID: {session_id})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register session {session_name}: {e}")
            return False
    
    async def authenticate_session(self, session_name: str, phone_number: str, verification_code: Optional[str] = None) -> Dict[str, Any]:
        """Authenticate a session with Telegram."""
        try:
            # Check if session exists in database
            session_info = await self.database.get_session_info(session_name)
            if not session_info:
                logger.error(f"Session {session_name} not found in database")
                return {"success": False, "error": "Session not found", "needs_otp": False}
            
            # Use base session manager for authentication
            auth_result = await self.base_session_manager.authenticate_session(
                session_name, phone_number, verification_code
            )
            
            if auth_result.get("success"):
                # Update session health after successful authentication
                await self.database.update_session_health(
                    session_name, 
                    "healthy", 
                    datetime.utcnow()
                )
                
                # Update metadata
                session_info.metadata_info = session_info.metadata_info or {}
                session_info.metadata_info["last_auth_time"] = datetime.utcnow().isoformat()
                session_info.metadata_info["auth_success"] = True
                session_info.metadata_info["authentication_pending"] = False
                
                # Mark session as active
                session_info.is_active = True
                
                logger.info(f"Successfully authenticated session: {session_name}")
                return {"success": True, "needs_otp": False}
            
            elif auth_result.get("needs_code"):
                # OTP verification needed
                logger.info(f"OTP verification required for session: {session_name}")
                return {"success": False, "needs_otp": True, "message": "Please check your phone for verification code"}
            
            else:
                # Authentication failed
                await self.database.update_session_health(
                    session_name, 
                    "auth_failed", 
                    datetime.utcnow()
                )
                
                logger.error(f"Authentication failed for session: {session_name}")
                return {"success": False, "needs_otp": False, "error": auth_result.get("error", "Authentication failed")}
            
        except Exception as e:
            logger.error(f"Failed to authenticate session {session_name}: {e}")
            return {"success": False, "error": str(e), "needs_otp": False}
    
    async def delete_session(self, session_name: str, force: bool = False) -> bool:
        """Delete a session with safety checks."""
        try:
            # Check if session has active pairs
            pairs = await self.database.get_pairs_by_session(session_name)
            
            if pairs and not force:
                logger.warning(f"Cannot delete session {session_name}: has {len(pairs)} active pairs")
                return False
            
            # Reassign pairs if forced deletion
            if pairs and force:
                logger.info(f"Force deleting session {session_name}, reassigning {len(pairs)} pairs")
                await self._emergency_reassign_pairs(pairs)
            
            # Remove from base session manager
            await self.base_session_manager.delete_session(session_name)
            
            # Update database
            await self.database.update_session_health(session_name, "deleted", datetime.utcnow())
            
            # Remove from worker groups
            await self._remove_session_from_workers(session_name)
            
            logger.info(f"Successfully deleted session: {session_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete session {session_name}: {e}")
            return False
    
    async def bulk_reassign_session(self, pair_ids: List[int], new_session_name: str) -> Dict[str, Any]:
        """Bulk reassign pairs to a new session with comprehensive validation."""
        result = {
            "success": False,
            "reassigned_pairs": [],
            "failed_pairs": [],
            "session_health": None,
            "worker_assignments": {}
        }
        
        try:
            # Validate new session
            new_session = await self.database.get_session_info(new_session_name)
            if not new_session or not new_session.is_active:
                result["error"] = f"Target session {new_session_name} is not available"
                return result
            
            # Check session capacity
            current_pair_count = new_session.pair_count
            if current_pair_count + len(pair_ids) > new_session.max_pairs:
                result["error"] = f"Session {new_session_name} would exceed capacity ({current_pair_count + len(pair_ids)} > {new_session.max_pairs})"
                return result
            
            # Perform health check on target session
            health_check = await self._perform_health_check(new_session_name)
            result["session_health"] = asdict(health_check)
            
            if not health_check.is_healthy:
                result["error"] = f"Target session {new_session_name} is unhealthy: {health_check.error_message}"
                return result
            
            # Begin reassignment process
            logger.info(f"Starting bulk reassignment of {len(pair_ids)} pairs to session {new_session_name}")
            
            # Update pairs in database
            success = await self.database.bulk_reassign_session(pair_ids, new_session_name, new_session.id)
            
            if success:
                # Update session pair counts
                await self._update_all_session_counts()
                
                # Reorganize worker groups
                await self._reorganize_workers_for_session(new_session_name)
                
                result["success"] = True
                result["reassigned_pairs"] = pair_ids
                
                logger.info(f"Successfully reassigned {len(pair_ids)} pairs to session {new_session_name}")
            else:
                result["error"] = "Database reassignment failed"
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to bulk reassign pairs: {e}")
            result["error"] = str(e)
            return result
    
    async def get_session_status(self, session_name: str) -> Dict[str, Any]:
        """Get comprehensive session status."""
        try:
            session_info = await self.database.get_session_info(session_name)
            if not session_info:
                return {"error": "Session not found"}
            
            pairs = await self.database.get_pairs_by_session(session_name)
            health_check = self.session_health_cache.get(session_name)
            
            worker_info = None
            for worker_id, worker_group in self.worker_groups.items():
                if worker_group.session_name == session_name:
                    worker_info = {
                        "worker_id": worker_id,
                        "is_active": worker_group.is_active,
                        "pair_count": len(worker_group.pair_ids),
                        "last_health_check": worker_group.last_health_check.isoformat() if worker_group.last_health_check else None
                    }
                    break
            
            return {
                "session_info": asdict(session_info),
                "pair_count": len(pairs),
                "pairs": [asdict(pair) for pair in pairs],
                "health_status": asdict(health_check) if health_check else None,
                "worker_info": worker_info,
                "capacity_usage": f"{len(pairs)}/{session_info.max_pairs}",
                "utilization_percent": round((len(pairs) / session_info.max_pairs) * 100, 2)
            }
            
        except Exception as e:
            logger.error(f"Failed to get session status for {session_name}: {e}")
            return {"error": str(e)}
    
    async def get_optimal_session_for_assignment(self) -> Optional[str]:
        """Find the best session for assigning new pairs."""
        try:
            sessions = await self.database.get_all_sessions()
            
            # Filter healthy, active sessions with capacity
            available_sessions = []
            for session in sessions:
                if (session.is_active and 
                    session.health_status == "healthy" and 
                    session.pair_count < session.max_pairs):
                    available_sessions.append(session)
            
            if not available_sessions:
                return None
            
            # Sort by priority (highest first), then by lowest utilization
            available_sessions.sort(
                key=lambda s: (-s.priority, s.pair_count / s.max_pairs)
            )
            
            return available_sessions[0].name
            
        except Exception as e:
            logger.error(f"Failed to find optimal session: {e}")
            return None
    
    # Private methods for internal operations
    
    async def _initialize_sessions(self):
        """Initialize session data from database."""
        try:
            sessions = await self.database.get_all_sessions()
            logger.info(f"Initializing {len(sessions)} sessions")
            
            for session in sessions:
                if session.is_active:
                    # Create worker group if needed
                    await self._ensure_worker_group_for_session(session.name)
                    
                    # Schedule initial health check
                    health_check = await self._perform_health_check(session.name)
                    self.session_health_cache[session.name] = health_check
            
            logger.info("Session initialization completed")
            
        except Exception as e:
            logger.error(f"Failed to initialize sessions: {e}")
            raise
    
    async def _health_monitor_loop(self):
        """Background health monitoring loop."""
        while self.running:
            try:
                await asyncio.sleep(self.health_check_interval)
                if not self.running:
                    break
                
                sessions = await self.database.get_all_sessions()
                
                for session in sessions:
                    if session.is_active:
                        health_check = await self._perform_health_check(session.name)
                        self.session_health_cache[session.name] = health_check
                        
                        # Update database
                        await self.database.update_session_health(
                            session.name,
                            health_check.status,
                            health_check.last_verified
                        )
                        
                        # Handle unhealthy sessions
                        if not health_check.is_healthy:
                            await self._handle_unhealthy_session(session.name, health_check)
                
                logger.debug("Health monitoring cycle completed")
                
            except Exception as e:
                logger.error(f"Error in health monitor loop: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def _cleanup_loop(self):
        """Background cleanup loop."""
        while self.running:
            try:
                await asyncio.sleep(3600)  # Run every hour
                if not self.running:
                    break
                
                # Clean up expired sessions
                await self._cleanup_expired_sessions()
                
                # Update session pair counts
                await self._update_all_session_counts()
                
                # Clean up inactive worker groups
                await self._cleanup_inactive_workers()
                
                logger.debug("Cleanup cycle completed")
                
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(300)  # Wait before retrying
    
    async def _worker_manager_loop(self):
        """Background worker management loop."""
        while self.running:
            try:
                await asyncio.sleep(180)  # Run every 3 minutes
                if not self.running:
                    break
                
                # Check worker group health
                for worker_id, worker_group in list(self.worker_groups.items()):
                    if worker_group.is_active:
                        await self._check_worker_group_health(worker_group)
                
                # Rebalance workers if needed
                await self._rebalance_worker_groups()
                
                logger.debug("Worker management cycle completed")
                
            except Exception as e:
                logger.error(f"Error in worker manager loop: {e}")
                await asyncio.sleep(120)  # Wait before retrying
    
    async def _perform_health_check(self, session_name: str) -> SessionHealthCheck:
        """Perform comprehensive health check on a session."""
        try:
            # Basic session existence check
            session_data = await self.base_session_manager.get_session(session_name)
            if not session_data:
                return SessionHealthCheck(
                    session_name=session_name,
                    is_healthy=False,
                    status="not_found",
                    last_verified=datetime.utcnow(),
                    error_message="Session data not found"
                )
            
            # Check session file validity
            # This would involve actual Telethon client validation in production
            
            # For now, simulate health check
            is_healthy = True
            status = "healthy"
            error_message = None
            
            # Check pair access (simplified)
            pairs = await self.database.get_pairs_by_session(session_name)
            pair_access_status = {}
            for pair in pairs:
                # Simulate access check
                pair_access_status[pair.id] = True
            
            return SessionHealthCheck(
                session_name=session_name,
                is_healthy=is_healthy,
                status=status,
                last_verified=datetime.utcnow(),
                error_message=error_message,
                pair_access_status=pair_access_status
            )
            
        except Exception as e:
            logger.error(f"Health check failed for session {session_name}: {e}")
            return SessionHealthCheck(
                session_name=session_name,
                is_healthy=False,
                status="error",
                last_verified=datetime.utcnow(),
                error_message=str(e)
            )
    
    async def _ensure_worker_group_for_session(self, session_name: str) -> str:
        """Ensure there's a worker group for the session."""
        # Check if session already has a worker group
        for worker_id, worker_group in self.worker_groups.items():
            if worker_group.session_name == session_name and worker_group.is_active:
                return worker_id
        
        # Create new worker group
        worker_id = f"worker_{session_name}_{uuid.uuid4().hex[:8]}"
        pairs = await self.database.get_pairs_by_session(session_name)
        
        worker_group = WorkerGroup(
            worker_id=worker_id,
            session_name=session_name,
            pair_ids=[pair.id for pair in pairs],
            max_pairs=min(self.max_pairs_per_session, 30)
        )
        
        self.worker_groups[worker_id] = worker_group
        
        # Update database with worker assignment
        for pair in pairs:
            pair.worker_id = worker_id
            await self.database.update_pair(pair)
        
        logger.info(f"Created worker group {worker_id} for session {session_name} with {len(pairs)} pairs")
        return worker_id
    
    async def _reorganize_workers_for_session(self, session_name: str):
        """Reorganize worker groups for a session after changes."""
        try:
            # Get all pairs for the session
            pairs = await self.database.get_pairs_by_session(session_name)
            
            # Group pairs into worker groups (max 30 per group)
            worker_groups_needed = (len(pairs) + self.max_pairs_per_session - 1) // self.max_pairs_per_session
            
            # Remove old worker groups for this session
            old_workers = [wid for wid, wg in self.worker_groups.items() if wg.session_name == session_name]
            for worker_id in old_workers:
                del self.worker_groups[worker_id]
            
            # Create new worker groups
            for i in range(worker_groups_needed):
                start_idx = i * self.max_pairs_per_session
                end_idx = min(start_idx + self.max_pairs_per_session, len(pairs))
                group_pairs = pairs[start_idx:end_idx]
                
                worker_id = f"worker_{session_name}_{i}_{uuid.uuid4().hex[:8]}"
                worker_group = WorkerGroup(
                    worker_id=worker_id,
                    session_name=session_name,
                    pair_ids=[pair.id for pair in group_pairs],
                    max_pairs=self.max_pairs_per_session
                )
                
                self.worker_groups[worker_id] = worker_group
                
                # Update pairs with new worker assignment
                for pair in group_pairs:
                    pair.worker_id = worker_id
                    await self.database.update_pair(pair)
            
            logger.info(f"Reorganized {worker_groups_needed} worker groups for session {session_name}")
            
        except Exception as e:
            logger.error(f"Failed to reorganize workers for session {session_name}: {e}")
    
    async def _update_all_session_counts(self):
        """Update pair counts for all sessions."""
        try:
            sessions = await self.database.get_all_sessions()
            for session in sessions:
                await self.database.update_session_pair_count(session.name)
            
        except Exception as e:
            logger.error(f"Failed to update session counts: {e}")
    
    async def _emergency_reassign_pairs(self, pairs: List[ForwardingPair]):
        """Emergency reassignment of pairs when a session is deleted."""
        try:
            for pair in pairs:
                # Find optimal session for reassignment
                optimal_session = await self.get_optimal_session_for_assignment()
                
                if optimal_session:
                    pair.session_name = optimal_session
                    pair.health_status = "reassigning"
                    await self.database.update_pair(pair)
                    logger.info(f"Emergency reassigned pair {pair.id} to session {optimal_session}")
                else:
                    # Disable pair if no sessions available
                    pair.is_active = False
                    pair.health_status = "orphaned"
                    await self.database.update_pair(pair)
                    logger.warning(f"Disabled orphaned pair {pair.id} - no sessions available")
            
        except Exception as e:
            logger.error(f"Failed to emergency reassign pairs: {e}")
    
    async def _handle_unhealthy_session(self, session_name: str, health_check: SessionHealthCheck):
        """Handle an unhealthy session."""
        try:
            logger.warning(f"Handling unhealthy session {session_name}: {health_check.error_message}")
            
            # Get pairs for this session
            pairs = await self.database.get_pairs_by_session(session_name)
            
            if health_check.status in ["expired", "unauthorized"]:
                # Session needs re-authentication or is permanently failed
                logger.error(f"Session {session_name} is {health_check.status}, disabling {len(pairs)} pairs")
                
                # Disable pairs temporarily
                for pair in pairs:
                    pair.health_status = f"session_{health_check.status}"
                    await self.database.update_pair(pair)
            
            # Additional recovery logic could be implemented here
            
        except Exception as e:
            logger.error(f"Failed to handle unhealthy session {session_name}: {e}")
    
    async def _cleanup_expired_sessions(self):
        """Clean up expired and inactive sessions."""
        try:
            cutoff_time = datetime.utcnow() - timedelta(seconds=self.session_timeout)
            sessions = await self.database.get_all_sessions()
            
            for session in sessions:
                if (session.last_verified and 
                    session.last_verified < cutoff_time and 
                    session.health_status in ["unhealthy", "error"]):
                    
                    logger.info(f"Cleaning up expired session: {session.name}")
                    await self.database.update_session_health(session.name, "expired", datetime.utcnow())
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {e}")
    
    async def _cleanup_inactive_workers(self):
        """Clean up inactive worker groups."""
        try:
            inactive_workers = [
                worker_id for worker_id, worker_group in self.worker_groups.items()
                if not worker_group.is_active
            ]
            
            for worker_id in inactive_workers:
                del self.worker_groups[worker_id]
                logger.debug(f"Cleaned up inactive worker: {worker_id}")
            
        except Exception as e:
            logger.error(f"Failed to cleanup inactive workers: {e}")
    
    async def _check_worker_group_health(self, worker_group: WorkerGroup):
        """Check health of a specific worker group."""
        try:
            # Update last health check
            worker_group.last_health_check = datetime.utcnow()
            
            # Verify all pairs still exist and are active
            valid_pairs = []
            for pair_id in worker_group.pair_ids:
                pair = await self.database.get_pair(pair_id)
                if pair and pair.is_active and pair.session_name == worker_group.session_name:
                    valid_pairs.append(pair_id)
            
            # Update worker group if pairs have changed
            if len(valid_pairs) != len(worker_group.pair_ids):
                logger.info(f"Updating worker group {worker_group.worker_id}: {len(worker_group.pair_ids)} -> {len(valid_pairs)} pairs")
                worker_group.pair_ids = valid_pairs
            
        except Exception as e:
            logger.error(f"Failed to check worker group health {worker_group.worker_id}: {e}")
    
    async def _rebalance_worker_groups(self):
        """Rebalance worker groups for optimal distribution."""
        try:
            # Group workers by session
            session_workers = {}
            for worker_id, worker_group in self.worker_groups.items():
                if worker_group.is_active:
                    if worker_group.session_name not in session_workers:
                        session_workers[worker_group.session_name] = []
                    session_workers[worker_group.session_name].append(worker_group)
            
            # Check if any sessions need rebalancing
            for session_name, workers in session_workers.items():
                total_pairs = sum(len(w.pair_ids) for w in workers)
                
                # If we have too many small worker groups, consolidate
                if len(workers) > 1 and total_pairs <= self.max_pairs_per_session:
                    logger.info(f"Consolidating {len(workers)} worker groups for session {session_name}")
                    await self._reorganize_workers_for_session(session_name)
            
        except Exception as e:
            logger.error(f"Failed to rebalance worker groups: {e}")
    
    async def _remove_session_from_workers(self, session_name: str):
        """Remove a session from all worker groups."""
        try:
            workers_to_remove = [
                worker_id for worker_id, worker_group in self.worker_groups.items()
                if worker_group.session_name == session_name
            ]
            
            for worker_id in workers_to_remove:
                del self.worker_groups[worker_id]
                logger.debug(f"Removed worker group {worker_id} for deleted session {session_name}")
            
        except Exception as e:
            logger.error(f"Failed to remove session {session_name} from workers: {e}")