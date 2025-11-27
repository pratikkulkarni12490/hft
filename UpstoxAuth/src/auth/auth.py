"""Core authentication module for Upstox API."""

import requests
from urllib.parse import urlencode, urlparse, parse_qs
from typing import Optional, Tuple
from datetime import datetime

from ..config import Config, Credentials
from ..utils import Logger, TimeUtils, ErrorHandler
from .token_storage import TokenStorage, TokenData


class TokenManager:
    """Manages token generation, storage, and refresh."""
    
    def __init__(self, config: Config):
        """Initialize TokenManager.
        
        Args:
            config: Config object with credentials and settings.
        """
        self.config = config
        self.logger = Logger.get()
        self.storage = TokenStorage(self.config.TOKEN_FILE)
        self.current_token: Optional[TokenData] = None
        
        # Try to load existing valid token
        self._load_stored_token()
    
    def _load_stored_token(self) -> bool:
        """Load and validate stored token.
        
        Returns:
            True if valid token loaded, False otherwise.
        """
        token_data = self.storage.get_valid_token()
        
        if token_data:
            self.current_token = token_data
            self.logger.debug(f"Loaded valid cached token for {token_data.user_name}")
            return True
        
        self.logger.debug("No valid cached token found")
        return False
    
    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """Generate authorization URL for user login.
        
        Args:
            state: Optional state parameter for security.
        
        Returns:
            Authorization URL to redirect user to.
        """
        if not self.config.credentials.validate():
            raise ValueError("Credentials not configured properly")
        
        params = {
            "client_id": self.config.credentials.client_id,
            "redirect_uri": self.config.credentials.redirect_uri,
            "response_type": "code"
        }
        
        if state:
            params["state"] = state
        
        auth_url = f"{self.config.AUTH_ENDPOINT}?{urlencode(params)}"
        return auth_url
    
    def exchange_code_for_token(self, auth_code: str) -> bool:
        """Exchange authorization code for access token.
        
        Args:
            auth_code: Authorization code from Upstox callback.
        
        Returns:
            True if successful, False otherwise.
        """
        if not self.config.credentials.validate():
            self.logger.error("Credentials not configured")
            return False
        
        payload = {
            "code": auth_code,
            "client_id": self.config.credentials.client_id,
            "client_secret": self.config.credentials.client_secret,
            "redirect_uri": self.config.credentials.redirect_uri,
            "grant_type": "authorization_code"
        }
        
        headers = {
            "accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        try:
            self.logger.debug("Exchanging authorization code for access token...")
            response = requests.post(
                self.config.TOKEN_ENDPOINT,
                data=payload,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            
            token_response = response.json()
            
            # Validate response
            required_fields = ["access_token", "user_id", "user_name", "email"]
            if not ErrorHandler.validate_response(token_response, required_fields):
                return False
            
            # Create token data
            issued_time = datetime.now()
            expiry_time = TimeUtils.get_token_expiry_time(issued_time)
            
            token_data = TokenData(
                access_token=token_response["access_token"],
                user_id=token_response["user_id"],
                user_name=token_response["user_name"],
                email=token_response["email"],
                broker=token_response.get("broker", ""),
                issued_at=issued_time.isoformat(),
                expires_at=expiry_time.isoformat(),
                exchanges=token_response.get("exchanges", []),
                products=token_response.get("products", []),
                order_types=token_response.get("order_types", []),
                extended_token=token_response.get("extended_token")
            )
            
            # Store token
            if self.storage.save_token(token_data):
                self.current_token = token_data
                self.logger.debug(
                    f"Successfully authenticated user: {token_data.user_name} "
                    f"(expires at {token_data.expires_at})"
                )
                return True
            
            return False
        
        except requests.exceptions.RequestException as e:
            ErrorHandler.handle_exception(e, "Failed to exchange authorization code")
            return False
    
    def get_access_token(self) -> Optional[str]:
        """Get current valid access token.
        
        Automatically loads cached token if available and not expired.
        
        Returns:
            Access token string if available, None otherwise.
        """
        if self.current_token and not self.current_token.is_expired():
            return self.current_token.access_token
        
        # Try to load from storage again
        if self._load_stored_token():
            return self.current_token.access_token
        
        self.logger.debug("No valid access token available")
        return None
    
    def is_token_valid(self) -> bool:
        """Check if current token is valid and not expired.
        
        Returns:
            True if token exists and is valid, False otherwise.
        """
        if not self.current_token:
            self._load_stored_token()
        
        if not self.current_token:
            return False
        
        return not self.current_token.is_expired()
    
    def get_token_info(self) -> Optional[dict]:
        """Get information about current token.
        
        Returns:
            Dictionary with token info, or None if no valid token.
        """
        if not self.is_token_valid():
            return None
        
        remaining_time = TimeUtils.get_time_until_expiry(
            self.current_token.get_issued_datetime()
        )
        
        return {
            "user_id": self.current_token.user_id,
            "user_name": self.current_token.user_name,
            "email": self.current_token.email,
            "issued_at": self.current_token.issued_at,
            "expires_at": self.current_token.expires_at,
            "remaining_time_seconds": remaining_time.total_seconds(),
            "exchanges": self.current_token.exchanges,
            "products": self.current_token.products,
            "order_types": self.current_token.order_types
        }
    
    def logout(self) -> bool:
        """Clear stored token and logout.
        
        Returns:
            True if successful, False otherwise.
        """
        if self.storage.clear():
            self.current_token = None
            self.logger.debug("Logged out successfully")
            return True
        
        return False
    
    def refresh_if_needed(self) -> bool:
        """Check and refresh token if needed (wrapper for future refresh logic).
        
        Currently, since Upstox doesn't provide a refresh endpoint,
        this method checks if token is still valid.
        
        Returns:
            True if token is valid, False if expired.
        """
        if self.is_token_valid():
            return True
        
        self.logger.debug("Token has expired or is invalid")
        return False


class UpstoxAuthenticator:
    """High-level authentication wrapper."""
    
    def __init__(self, 
                 credentials: Optional[Credentials] = None,
                 config: Optional[Config] = None):
        """Initialize Upstox authenticator.
        
        Args:
            credentials: Upstox credentials. If None, loads from config.
            config: Config object. If None, creates with default settings.
        """
        if config is None:
            config = Config(credentials=credentials)
        
        self.config = config
        self.logger = Logger.get()
        self.token_manager = TokenManager(config)
    
    def authenticate(self, auth_code: str) -> bool:
        """Authenticate using authorization code.
        
        Args:
            auth_code: Authorization code from Upstox callback.
        
        Returns:
            True if authentication successful, False otherwise.
        """
        return self.token_manager.exchange_code_for_token(auth_code)
    
    def get_login_url(self, state: Optional[str] = None) -> str:
        """Get URL for user to login.
        
        Args:
            state: Optional state parameter for security.
        
        Returns:
            Login URL.
        """
        return self.token_manager.get_authorization_url(state)
    
    def get_token(self) -> Optional[str]:
        """Get current valid access token.
        
        Returns:
            Access token if available, None otherwise.
        """
        return self.token_manager.get_access_token()
    
    def is_authenticated(self) -> bool:
        """Check if user is authenticated with valid token.
        
        Returns:
            True if authenticated, False otherwise.
        """
        return self.token_manager.is_token_valid()
    
    def get_status(self) -> dict:
        """Get authentication status.
        
        Returns:
            Dictionary with authentication status and token info.
        """
        is_valid = self.token_manager.is_token_valid()
        token_info = self.token_manager.get_token_info()
        
        return {
            "is_authenticated": is_valid,
            "token_info": token_info,
            "message": "Authenticated" if is_valid else "Not authenticated"
        }
    
    def logout(self) -> bool:
        """Logout and clear stored token.
        
        Returns:
            True if successful, False otherwise.
        """
        return self.token_manager.logout()
