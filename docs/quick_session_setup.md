# Quick Session Setup - Super Easy Guide

## One Command Setup (Recommended)

### Step 1: Create Session & Get OTP
```
/quicksession my_session +1234567890
```
**What this does:**
- Registers your session automatically
- Sends OTP to your phone immediately  
- Sets up everything with good defaults

### Step 2: Enter Your Verification Code
```
/entercode my_session 12345
```
**Replace 12345 with the code from your Telegram app**

### Done! Your session is ready!

## Check Your Setup
```
/sessionstatus my_session
```
Should show: ✅ healthy, 🟢 active

## Alternative Commands

### Check Pending Sessions
```
/pendingsessions
```
Shows sessions waiting for OTP codes

### Get Help
```
/sessionguide
```
Shows detailed instructions

### Advanced Setup (if needed)
```
/registersession my_session +1234567890 5 30
/authenticate my_session
/authenticate my_session 12345
```

## Tips for Success

1. **Phone Number Format**: Always include country code
   - ✅ `+1234567890` 
   - ❌ `1234567890`

2. **Session Names**: Keep it simple
   - ✅ `my_session`, `backup`, `main_account`
   - ❌ `my-session@2024`, `user#1`

3. **OTP Timing**: 
   - Check Telegram app immediately
   - Codes expire in 5 minutes
   - Use `/quicksession` again if expired

4. **Multiple Sessions**:
   - Each session handles 30 pairs
   - Higher priority = gets new pairs first
   - Use different phone numbers for each session

## Common Issues

**"Session already exists"**
- Choose a different session name
- Or check `/sessionstatus` to see existing sessions

**"Invalid verification code"**  
- Double-check the 5-digit code from Telegram
- Make sure it hasn't expired
- Try `/quicksession` again for new code

**"Failed to send code"**
- Verify phone number has country code
- Make sure you have Telegram on that number
- Contact admin if persistent

**"No pending sessions"**
- Use `/quicksession` first to create session
- Check `/sessionstatus` for already active sessions

## Emergency Recovery

If something goes wrong:
1. Use `/pendingsessions` to see what's waiting
2. Use `/sessionstatus` to see active sessions  
3. Start fresh with new session name if needed
4. Contact admin for help with persistent issues

The new simplified system makes session setup much easier while maintaining all the advanced features for power users.