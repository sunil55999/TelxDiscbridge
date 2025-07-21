# Advanced Session Management Documentation

## Overview

The Advanced Session Management system provides sophisticated multi-session support for the Telegram → Discord → Telegram forwarding bot. This system enables secure management of dozens of concurrent Telegram sessions across hundreds of forwarding pairs with dynamic scaling, health monitoring, and administrative controls.

## Key Features

### 1. Session Abstraction & Management
- **Centralized Session Registry**: All sessions stored securely with metadata including status, associations, and health information
- **Session Lifecycle Management**: Complete CRUD operations for session registration, authentication, health verification, and deletion
- **Enhanced Session Information**: Priority levels, capacity limits, worker assignments, and custom metadata support

### 2. Worker Segregation
- **Automatic Worker Groups**: Each 20-30 pairs per session run in isolated worker groups
- **Process Isolation**: Session failures only affect their associated worker groups
- **Dynamic Rebalancing**: Automatic worker group reorganization when sessions change

### 3. Bulk Operations
- **Bulk Session Reassignment**: Move multiple pairs between sessions in a single operation
- **Capacity Validation**: Pre-flight checks for session health and capacity before reassignment
- **Audit Logging**: Comprehensive logging of all session assignment changes

### 4. Health Monitoring
- **Continuous Health Checks**: Automated monitoring of session health every 5 minutes
- **Access Verification**: Validation of pair-level access permissions
- **Automatic Recovery**: Intelligent handling of unhealthy sessions with fallback strategies

### 5. Security & Configuration
- **Encrypted Session Storage**: All session files encrypted with master key
- **Admin Access Control**: Whitelist-based admin permissions for all session operations
- **Comprehensive Logging**: Detailed audit trails for security and debugging

## Admin Commands

### Session Registration
```
/registersession <session_name> <phone_number> [priority] [max_pairs]
```
Register a new Telegram user session for forwarding pairs.

**Parameters:**
- `session_name`: Unique identifier for the session (alphanumeric + underscores)
- `phone_number`: Telegram phone number for the session
- `priority`: Session priority for pair assignment (1-10, higher = better)
- `max_pairs`: Maximum pairs this session can handle (1-50, default: 30)

**Example:**
```
/registersession user1_main +1234567890 3 25
```

### Session Authentication
```
/authenticate <session_name> [verification_code]
```
Authenticate a registered session with Telegram.

**Parameters:**
- `session_name`: Name of the session to authenticate
- `verification_code`: Optional Telegram verification code

**Example:**
```
/authenticate user1_main 12345
```

### Session Status
```
/sessionstatus [session_name]
```
View detailed status for a specific session or overview of all sessions.

**Examples:**
```
/sessionstatus user1_main    # Specific session details
/sessionstatus               # All sessions overview
```

### Bulk Session Reassignment
```
/changesession <new_session_name> <pair_specification>
```
Reassign pairs to a different session in bulk.

**Pair Specifications:**
- `1,2,3,4`: Comma-separated pair IDs
- `1-10`: Range of pair IDs
- `all_from:session_name`: All pairs from a specific session

**Examples:**
```
/changesession user2_backup 1,2,3,4,5
/changesession user3_main 10-20
/changesession user1_main all_from:user2_backup
```

### Session Health
```
/sessionhealth [session_name]
```
Check health status of sessions.

**Examples:**
```
/sessionhealth user1_main    # Detailed health for specific session
/sessionhealth               # Health overview for all sessions
```

### Session Deletion
```
/deletesession <session_name> [force]
```
Delete a session with safety checks.

**Parameters:**
- `session_name`: Name of session to delete
- `force`: Optional flag to delete sessions with active pairs (reassigns them)

**Examples:**
```
/deletesession old_session
/deletesession problematic_session force
```

### Optimal Session Selection
```
/optimalsession
```
Find the best session for new pair assignments based on priority, capacity, and health.

### Worker Status
```
/workerstatus
```
View status of all worker groups managing session pairs.

## Session Health States

### Health Status Values
- **healthy**: Session is fully operational and accessible
- **unhealthy**: Session has connectivity or access issues
- **expired**: Session authentication has expired
- **unauthorized**: Session lacks required permissions
- **unknown**: Health status not yet determined
- **deleted**: Session has been removed

### Automated Health Actions
- **5-minute intervals**: Regular health checks for all active sessions
- **Unhealthy detection**: Automatic notification and pair status updates
- **Expired sessions**: Automatic disabling of associated pairs
- **Recovery attempts**: Intelligent retry logic for temporary failures

## Worker Group Management

### Automatic Worker Creation
- **Session-based grouping**: Each session gets dedicated worker groups
- **Capacity limits**: Maximum 30 pairs per worker group
- **Process isolation**: Worker failures don't affect other sessions

### Worker Rebalancing
- **Load distribution**: Even pair distribution across workers
- **Dynamic scaling**: New workers created as pairs are added
- **Consolidation**: Underutilized workers automatically merged

### Worker Health Monitoring
- **Regular checks**: Worker health verified every 3 minutes
- **Pair validation**: Continuous verification of pair assignments
- **Automatic cleanup**: Inactive workers removed automatically

## Configuration Options

### Session Limits
- **Max pairs per session**: Configurable limit (default: 30)
- **Health check interval**: Monitoring frequency (default: 5 minutes)
- **Session timeout**: Expiration threshold (default: 1 hour)

### Worker Configuration
- **Max pairs per worker**: Worker capacity limit (default: 30)
- **Health check frequency**: Worker monitoring interval (default: 3 minutes)
- **Rebalance threshold**: Trigger for worker reorganization

### Security Settings
- **Admin whitelist**: User IDs authorized for session management
- **Session encryption**: Master key for session data protection
- **Audit logging**: Comprehensive operation logging

## Best Practices

### Session Naming
- Use descriptive, consistent naming conventions
- Include user identifier and purpose (e.g., `user1_main`, `backup_session`)
- Avoid special characters except underscores

### Capacity Planning
- Set realistic max_pairs limits based on device capabilities
- Higher priority sessions for critical forwarding pairs
- Regular monitoring of session utilization

### Health Monitoring
- Monitor session health dashboard regularly
- Respond promptly to unhealthy session alerts
- Maintain backup sessions for critical pairs

### Security
- Regularly audit admin user permissions
- Monitor session access patterns
- Use secure phone numbers for session registration

## Troubleshooting

### Common Issues

#### Session Authentication Failures
- Verify phone number format (+1234567890)
- Check Telegram verification code delivery
- Ensure session name doesn't already exist

#### Capacity Exceeded Errors
- Check session utilization with `/sessionstatus`
- Increase max_pairs limit if needed
- Distribute pairs across multiple sessions

#### Worker Group Issues
- Use `/workerstatus` to check worker health
- Restart bot if workers become unresponsive
- Monitor system resources during high load

#### Health Check Failures
- Verify network connectivity
- Check Telegram API access
- Review session permissions

### Error Recovery

#### Unhealthy Sessions
1. Check `/sessionhealth` for specific error details
2. Attempt re-authentication with `/authenticate`
3. If persistent, use `/changesession` to move pairs
4. Consider session deletion and recreation

#### Failed Bulk Operations
1. Review error message for specific issue
2. Check target session capacity and health
3. Split large operations into smaller batches
4. Verify pair IDs are valid and active

#### Worker Group Problems
1. Check `/workerstatus` for worker details
2. Restart bot to reset worker groups
3. Monitor system resources and memory usage
4. Reduce pairs per session if performance issues persist

## API Integration

The advanced session management system provides programmatic access through the `AdvancedSessionManager` class:

```python
# Register a new session
success = await advanced_session_manager.register_session(
    "api_session", "+1234567890", priority=2, max_pairs=25
)

# Get session status
status = await advanced_session_manager.get_session_status("api_session")

# Bulk reassign pairs
result = await advanced_session_manager.bulk_reassign_session(
    [1, 2, 3], "target_session"
)

# Find optimal session
optimal = await advanced_session_manager.get_optimal_session_for_assignment()
```

This comprehensive system ensures reliable, scalable, and secure management of multiple Telegram sessions for large-scale message forwarding operations.