# HFT Authentication Module

A modular, production-ready Python authentication system for Upstox High Frequency Trading platform.

## Features

✨ **Smart Token Management**
- Automatic OAuth 2.0 authentication with Upstox
- Token persistence and caching to avoid redundant API calls
- Automatic expiry detection (3:30 AM IST next day per Upstox rules)
- Intelligent token reuse across application restarts

🔐 **Modular & Secure**
- Separation of concerns (config, auth, storage, utils)
- Secure credential management with file encryption option
- Environment variable support for sensitive data
- Comprehensive error handling and logging

📊 **User Information Tracking**
- Stores user profile info (name, email, exchanges, products)
- Tracks token issue and expiry times
- Provides token status and remaining lifetime

🛠️ **Easy Integration**
- Simple, clean API for easy integration
- Minimal dependencies
- Ready for production use
- Extensible design for future enhancements

## Project Structure

```
HFT/
├── src/
│   ├── __init__.py           # Main module entry point
│   ├── auth/
│   │   ├── __init__.py       # Auth module exports
│   │   ├── auth.py           # Core authentication logic
│   │   └── token_storage.py  # Token persistence
│   ├── config/
│   │   ├── __init__.py       # Config module exports
│   │   ├── config.py         # Configuration handler
│   │   └── credentials.py    # Credentials management
│   └── utils/
│       └── __init__.py       # Utilities (logging, time, error handling)
├── examples/
│   └── demo.py               # Complete usage examples
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

## Installation

### 1. Clone or Download
```bash
cd /path/to/HFT
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Set Up Credentials

**Option A: Environment Variables** (Recommended for development)
```bash
export UPSTOX_CLIENT_ID="your_client_id"
export UPSTOX_CLIENT_SECRET="your_client_secret"
export UPSTOX_REDIRECT_URI="http://localhost:8080/callback"
```

**Option B: Credentials File**
```bash
# Create ~/.hft/credentials.json
{
  "client_id": "your_client_id",
  "client_secret": "your_client_secret",
  "redirect_uri": "http://localhost:8080/callback"
}
```

**Option C: Pass Directly in Code**
```python
from src.config import Credentials, Config
creds = Credentials(
    client_id="your_client_id",
    client_secret="your_client_secret",
    redirect_uri="http://localhost:8080/callback"
)
```

## Quick Start

### Basic Authentication Flow

```python
from src.auth import UpstoxAuthenticator
from src.config import Config, Credentials
from src.utils import Logger
from pathlib import Path

# Set up logging
Logger.setup(log_file=Path.home() / ".hft" / "logs" / "hft.log")

# Create authenticator (loads cached token if available)
auth = UpstoxAuthenticator()

# Check if already authenticated
if auth.is_authenticated():
    print("Already logged in!")
    status = auth.get_status()
    print(status)
else:
    # Get login URL and redirect user
    login_url = auth.get_login_url(state="random_state_string")
    print(f"Visit: {login_url}")
    
    # After user logs in, get the authorization code from redirect
    auth_code = input("Enter authorization code: ")
    
    # Exchange code for token
    if auth.authenticate(auth_code):
        print("Authentication successful!")
        token = auth.get_token()
        print(f"Access Token: {token}")
    else:
        print("Authentication failed")
```

### Using the Access Token

```python
# Token is automatically reused across restarts
auth = UpstoxAuthenticator()

if auth.is_authenticated():
    token = auth.get_token()
    
    # Use token in API headers
    import requests
    headers = {"Authorization": f"Bearer {token}"}
    
    # Make API calls
    response = requests.get(
        "https://api.upstox.com/v2/user/profile",
        headers=headers
    )
```

### Checking Token Status

```python
# Check if token is valid
if auth.is_authenticated():
    status = auth.get_status()
    print(status)
    # Output:
    # {
    #     'is_authenticated': True,
    #     'token_info': {
    #         'user_id': 'ABC123',
    #         'user_name': 'John Doe',
    #         'email': 'john@example.com',
    #         'issued_at': '2025-11-25T10:30:00',
    #         'expires_at': '2025-11-26T03:30:00',
    #         'remaining_time_seconds': 43200,
    #         'exchanges': ['NSE', 'NFO'],
    #         'products': ['D', 'CO', 'I'],
    #         'order_types': ['MARKET', 'LIMIT', 'SL', 'SL-M']
    #     },
    #     'message': 'Authenticated'
    # }

# Check if token needs refresh
if auth.token_manager.refresh_if_needed():
    print("Token is still valid")
else:
    print("Token expired, need to re-authenticate")
```

### Logout

```python
auth.logout()
print("Logged out successfully")
```

## API Reference

### UpstoxAuthenticator

Main high-level class for authentication.

```python
auth = UpstoxAuthenticator(credentials=None, config=None)

# Methods
auth.authenticate(auth_code: str) -> bool
auth.get_login_url(state: str = None) -> str
auth.get_token() -> Optional[str]
auth.is_authenticated() -> bool
auth.get_status() -> dict
auth.logout() -> bool
```

### TokenManager

Low-level token management.

```python
token_mgr = TokenManager(config)

# Methods
token_mgr.get_authorization_url(state: str = None) -> str
token_mgr.exchange_code_for_token(auth_code: str) -> bool
token_mgr.get_access_token() -> Optional[str]
token_mgr.is_token_valid() -> bool
token_mgr.get_token_info() -> Optional[dict]
token_mgr.logout() -> bool
token_mgr.refresh_if_needed() -> bool
```

### Config

Configuration management.

```python
config = Config(credentials=None, token_storage_dir=None)

# Methods
config.ensure_directories()
config.save_credentials()

# Class Variables
Config.UPSTOX_BASE_URL
Config.AUTH_ENDPOINT
Config.TOKEN_ENDPOINT
Config.TOKEN_STORAGE_DIR
Config.TOKEN_FILE
Config.CREDENTIALS_FILE
Config.LOG_FILE
```

### Credentials

Credentials management.

```python
creds = Credentials(client_id, client_secret, redirect_uri)

# Class Methods
Credentials.from_env() -> Credentials
Credentials.from_file(filepath: str) -> Credentials
Credentials.from_dict(data: dict) -> Credentials

# Instance Methods
creds.to_file(filepath: str)
creds.to_dict() -> dict
creds.validate() -> bool
```

### Logger

Centralized logging.

```python
from src.utils import Logger

logger = Logger.setup(log_file=None, level="INFO")
logger = Logger.get()  # Get existing logger

# Standard logging methods
logger.info("Message")
logger.debug("Debug message")
logger.warning("Warning")
logger.error("Error")
```

### TimeUtils

Time and expiry calculation utilities.

```python
from src.utils import TimeUtils
from datetime import datetime

# Calculate token expiry (3:30 AM IST next day)
expiry = TimeUtils.get_token_expiry_time(datetime.now())

# Check if expired
is_expired = TimeUtils.is_token_expired(issued_time)

# Get remaining time
remaining = TimeUtils.get_time_until_expiry(issued_time)

# Timestamp conversions
ts_ms = TimeUtils.datetime_to_timestamp_ms(datetime.now())
dt = TimeUtils.timestamp_ms_to_datetime(ts_ms)
```

## Token Storage

Tokens are stored securely in:
```
~/.hft/tokens/upstox_token.json
```

Token file format:
```json
{
  "access_token": "token_string...",
  "user_id": "USER123",
  "user_name": "John Doe",
  "email": "john@example.com",
  "broker": "UPSTOX",
  "issued_at": "2025-11-25T10:30:00",
  "expires_at": "2025-11-26T03:30:00",
  "exchanges": ["NSE", "NFO", "BSE"],
  "products": ["D", "CO", "I"],
  "order_types": ["MARKET", "LIMIT", "SL", "SL-M"],
  "extended_token": "extended_token_string..."
}
```

## Token Expiry Rules

Per Upstox API:
- **Regular Token**: Valid until **3:30 AM IST** the next calendar day
- **Extended Token**: Designed for read-only access with longer validity
- Tokens issued after 3:30 AM expire at 3:30 AM the same day
- Tokens issued before 3:30 AM expire at 3:30 AM the next day

## Upstox API Documentation

For more details on Upstox APIs:
- [Login & Authentication](https://upstox.com/developer/api-documentation/login/)
- [Authorize Endpoint](https://upstox.com/developer/api-documentation/authorize)
- [Get Token Endpoint](https://upstox.com/developer/api-documentation/get-token)
- [Access Token Request](https://upstox.com/developer/api-documentation/access-token-request)
- [Full API Documentation](https://upstox.com/developer/api-documentation/)

## Examples

Run the demo script to see all features:

```bash
python examples/demo.py
```

This displays:
- Credential setup examples
- Logger configuration
- Complete authentication flow
- Token management examples
- Time utility usage
- Full workflow example

## Error Handling

The module includes comprehensive error handling:

```python
from src.utils import Logger, ErrorHandler

logger = Logger.get()

try:
    auth = UpstoxAuthenticator()
    if auth.authenticate(auth_code):
        print("Success!")
except Exception as e:
    ErrorHandler.handle_exception(e, context="Authentication failed")
```

## Logging

All operations are logged:

```python
from src.utils import Logger
from pathlib import Path

# Set up logging
Logger.setup(
    log_file=Path.home() / ".hft" / "logs" / "hft.log",
    level="INFO"
)

logger = Logger.get()
logger.info("Application started")
```

Logs include:
- Authentication attempts
- Token generation and refresh
- Expiry checks
- Errors and exceptions
- API calls

## Best Practices

1. **Environment Variables**: Store credentials in environment variables for production
2. **Error Handling**: Always check return values and handle exceptions
3. **Logging**: Enable logging for debugging and monitoring
4. **Token Refresh**: Call `refresh_if_needed()` periodically to check expiry
5. **Secure Storage**: Consider encrypting credentials file for sensitive environments
6. **Rate Limiting**: Implement rate limiting for API calls using the same token

## Future Enhancements

- [ ] Automated token refresh endpoint (when Upstox provides one)
- [ ] Encrypted credentials file support
- [ ] OAuth token refresh handling
- [ ] Multi-user token management
- [ ] Webhook support for token expiry notifications
- [ ] Database persistence option
- [ ] Token caching with SQLite

## Troubleshooting

### "No valid access token available"
- Ensure credentials are properly configured
- Check environment variables or credentials file
- Run the authentication flow to get a new token

### "Token has expired"
- Token expires at 3:30 AM IST daily
- Initialize a new authenticator to reload token cache
- If token is expired, authenticate again

### "Credentials not configured properly"
- Verify all three credentials (client_id, client_secret, redirect_uri)
- Check environment variables or file path
- Validate credential format

### Logs not appearing
- Call `Logger.setup()` before using the module
- Check log file path is writable
- Verify log level is set correctly

## License

This module is provided as-is for use with Upstox trading platform.

## Support

For issues or questions:
1. Check the examples in `examples/demo.py`
2. Review the API documentation
3. Check logs in `~/.hft/logs/hft.log`
4. Visit [Upstox Community](https://community.upstox.com/)

---

**Happy Trading! 🚀**
