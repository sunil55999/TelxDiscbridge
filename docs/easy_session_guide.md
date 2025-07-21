# Easy Session Management Guide

## Quick Start - Adding a New Session

### Step 1: Register Your Session
```
/registersession my_session +1234567890 5 30
```
- `my_session` = Your session name (use letters, numbers, underscores only)
- `+1234567890` = Your Telegram phone number (with country code)
- `5` = Priority (1-10, higher is better for new pairs)
- `30` = Max pairs this session can handle

### Step 2: Start Authentication
```
/authenticate my_session
```
This will:
- Send an OTP code to your phone
- You'll get a message saying "Check your phone for verification code"

### Step 3: Enter Your OTP Code
```
/authenticate my_session 12345
```
- Replace `12345` with the actual code from Telegram
- Session will be activated and ready to use

### Step 4: Verify Success
```
/sessionstatus my_session
```
You should see:
- Health: healthy
- Active: Yes
- Ready for pairs

## Common Issues & Solutions

### "Session not found" Error
- Make sure you registered the session first with `/registersession`
- Check spelling of session name

### "Failed to send verification code"
- Verify phone number format: `+1234567890` (include country code)
- Make sure the phone number is correct
- Check if you have Telegram installed on that number

### "Invalid verification code"
- Double-check the code from your Telegram app
- Make sure code hasn't expired (usually 5 minutes)
- Try requesting a new code with `/authenticate sessionname` (without code)

### "Authentication failed"
- Start over with a new session name
- Make sure you have access to the phone number
- Contact admin if persistent issues

## Managing Multiple Sessions

### Check All Sessions
```
/sessionstatus
```
Shows overview of all your sessions with health status.

### Move Pairs Between Sessions
```
/changesession target_session 1,2,3,4,5
```
Moves pairs 1,2,3,4,5 to target_session.

### Find Best Session for New Pairs
```
/optimalsession
```
Shows which session has the best capacity and health.

### Session Health Check
```
/sessionhealth
```
Shows health status of all sessions.

## Best Practices

1. **Use Clear Names**: `user1_main`, `backup_session`, `high_priority`
2. **Set Appropriate Priorities**: Main sessions = 5-10, backup = 1-3
3. **Monitor Health**: Check `/sessionhealth` regularly
4. **Don't Overload**: Keep under 30 pairs per session for best performance
5. **Have Backups**: Register 2-3 sessions for redundancy

## Quick Commands Reference

| Command | Purpose | Example |
|---------|---------|---------|
| `/sessionhelp` | Show this guide | `/sessionhelp` |
| `/registersession` | Register new session | `/registersession name +phone` |
| `/authenticate` | Authenticate session | `/authenticate name [code]` |
| `/sessionstatus` | Check session status | `/sessionstatus [name]` |
| `/sessionhealth` | Check session health | `/sessionhealth` |
| `/optimalsession` | Find best session | `/optimalsession` |
| `/changesession` | Move pairs | `/changesession target 1,2,3` |

## Getting Help

- Use `/sessionhelp` anytime for this guide
- Use `/help` for basic bot commands
- Use `/sessionstatus` to check current state
- Contact admin for persistent authentication issues

The enhanced session management system now provides:
- Real OTP verification with Telegram
- Better error messages and guidance
- Step-by-step authentication flow
- Automatic session health monitoring
- Easy session switching and management