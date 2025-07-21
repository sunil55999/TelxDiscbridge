# Enhanced Admin Command Examples

## Session Management Commands

### 1. Register a new session
```
/registersession user1_main +1234567890 3 25
```
Creates a session with priority 3 and max capacity of 25 pairs.

### 2. Authenticate session
```
/authenticate user1_main
```
Starts authentication process for the session.

### 3. Check session status
```
/sessionstatus user1_main
```
Shows detailed status including health, worker info, and pairs.

### 4. View all sessions
```
/sessionstatus
```
Shows overview of all sessions with utilization.

### 5. Check session health
```
/sessionhealth
```
Shows health overview for all sessions.

### 6. Bulk reassign pairs
```
/changesession user2_backup 1,2,3,4,5
/changesession user3_main 10-20
/changesession user1_main all_from:old_session
```
Move specific pairs, ranges, or all pairs from a session.

### 7. Find optimal session
```
/optimalsession
```
Returns the best session for new pair assignments.

### 8. Check worker status
```
/workerstatus
```
Shows all worker groups and their pair distributions.

### 9. Delete session (with force)
```
/deletesession old_session force
```
Removes session and reassigns its pairs to optimal sessions.

## Example Session Management Workflow

### Initial Setup
1. **Register multiple sessions:**
   ```
   /registersession primary_user +1111111111 5 30
   /registersession backup_user +2222222222 3 25
   /registersession bulk_user +3333333333 1 40
   ```

2. **Authenticate sessions:**
   ```
   /authenticate primary_user
   /authenticate backup_user
   /authenticate bulk_user
   ```

3. **Check overall status:**
   ```
   /sessionstatus
   /sessionhealth
   ```

### Adding Forwarding Pairs
1. **Find optimal session:**
   ```
   /optimalsession
   ```

2. **Add pairs to optimal session:**
   ```
   /addpair "News Channel" -1001234567890 1234567890123456 -1009876543210 primary_user
   ```

3. **Monitor distribution:**
   ```
   /workerstatus
   ```

### Session Maintenance
1. **Regular health checks:**
   ```
   /sessionhealth
   ```

2. **Rebalance if needed:**
   ```
   /changesession backup_user 1-10
   ```

3. **Check specific session details:**
   ```
   /sessionstatus primary_user
   ```

### Emergency Procedures
1. **Handle unhealthy session:**
   ```
   /sessionhealth problematic_session
   /changesession backup_user all_from:problematic_session
   /deletesession problematic_session force
   ```

2. **Session recovery:**
   ```
   /registersession new_session +4444444444 5 30
   /authenticate new_session
   /changesession new_session 1-20
   ```

## Advanced Usage Patterns

### High-Priority Session Setup
```
/registersession vip_session +5555555555 10 20
/authenticate vip_session
/changesession vip_session all_from:regular_session
```

### Load Distribution
```
/sessionstatus                    # Check current load
/optimalsession                   # Find best session
/changesession optimal_session 21-30  # Move excess pairs
/workerstatus                     # Verify worker distribution
```

### Session Rotation
```
/registersession rotation_session +6666666666 5 30
/authenticate rotation_session
/changesession rotation_session all_from:old_session
/deletesession old_session force
```

## Monitoring Dashboard Commands

### Quick Status Check
```
/sessionstatus && /sessionhealth && /workerstatus
```

### Capacity Planning
```
/sessionstatus
/optimalsession
/workerstatus
```

### Health Monitoring
```
/sessionhealth
/sessionstatus problematic_session
```

These commands provide complete control over the advanced session management system, enabling efficient operation of large-scale message forwarding with multiple Telegram sessions.