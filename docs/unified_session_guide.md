# Unified Session Management Guide

## Overview

The session management system has been simplified to use a single, easy-to-use command: `/addsession`

## How to Add a New Session

### Step 1: Start the Process
Use the `/addsession` command with your session name and phone number:

```
/addsession my_session +1234567890
```

### Step 2: Wait for OTP
The bot will:
- Register your session
- Send a verification code to your phone
- Show interactive buttons for next steps

### Step 3: Enter Your Code
Click "Enter OTP Code" and send your verification code as a message:
```
12345
```

### Step 4: Ready to Use!
Your session is now active and ready for forwarding pairs.

## Command Syntax

```
/addsession <session_name> <phone_number>
```

**Parameters:**
- `session_name`: Letters, numbers, underscores only (e.g., `my_session`, `user_1`)
- `phone_number`: Must include country code (e.g., `+1234567890`, `+447123456789`)

## Examples

### US Phone Number
```
/addsession main_session +1234567890
```

### UK Phone Number
```
/addsession backup_session +447123456789
```

### India Phone Number
```
/addsession india_session +91987654321
```

## What Happens During Setup

1. **Validation**: Bot checks if session name and phone number are valid
2. **Registration**: Session is created in the system
3. **OTP Request**: Telegram sends verification code to your phone
4. **Interactive Buttons**: Bot shows options to enter code, resend, or cancel
5. **Code Entry**: You send your verification code as a regular message
6. **Verification**: Bot confirms the code with Telegram
7. **Activation**: Session becomes active and ready for use

## Interactive Features

### Button Options
- **Enter OTP Code**: Click to enter verification mode
- **Resend OTP**: Request a new verification code
- **Cancel**: Stop the setup process

### Automatic Features
- **Input Validation**: Prevents invalid session names and phone numbers
- **Duplicate Prevention**: Won't create sessions that already exist
- **Error Recovery**: Automatic cleanup if setup fails
- **Timeout Protection**: Verification expires after 10 minutes

## Error Handling

### Common Issues
- **Invalid Session Name**: Use only letters, numbers, and underscores
- **Wrong Phone Format**: Must start with country code (+1, +44, etc.)
- **Session Exists**: Choose a different name if session already exists
- **OTP Timeout**: Start over if verification takes too long

### Recovery
If something goes wrong, simply run `/addsession` again with the same or different session name.

## Tips for Success

1. **Have Your Phone Ready**: Keep your phone accessible for OTP
2. **Use Simple Names**: Choose clear session names like `main_session` or `backup_1`
3. **Include Country Code**: Always use full international format (+1234567890)
4. **Check OTP Quickly**: Verification codes usually arrive within 30 seconds
5. **Delete Failed Sessions**: If setup fails, the system cleans up automatically

## Getting Help

- **No Parameters**: Run `/addsession` without parameters for help
- **Examples**: The help shows specific examples for different countries
- **Support**: Contact admin if you encounter persistent issues

## Advanced Features

The unified system includes:
- **Automatic Cleanup**: Failed sessions are removed automatically
- **Multi-Step Validation**: Each input is checked before proceeding
- **Interactive Guidance**: Buttons and messages guide you through the process
- **Robust Error Handling**: Clear error messages with suggested fixes
- **Security**: OTP messages are automatically deleted for privacy

This simplified approach replaces the previous complex multi-command system with a single, user-friendly workflow.