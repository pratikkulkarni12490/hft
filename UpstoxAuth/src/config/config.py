"""Configuration handler for HFT application."""

import os
from pathlib import Path
from typing import Optional
from .credentials import Credentials


class Config:
    """Application configuration management."""
    
    # API endpoints
    UPSTOX_BASE_URL = "https://api.upstox.com/v2"
    AUTH_ENDPOINT = f"{UPSTOX_BASE_URL}/login/authorization/dialog"
    TOKEN_ENDPOINT = f"{UPSTOX_BASE_URL}/login/authorization/token"
    
    # Token expiry time (3:30 AM IST next day, in seconds from epoch)
    # This is a placeholder; actual calculation happens at runtime
    TOKEN_EXPIRY_HOUR = 3
    TOKEN_EXPIRY_MINUTE = 30
    
    # Token storage
    TOKEN_STORAGE_DIR = Path.home() / ".hft" / "tokens"
    TOKEN_FILE = TOKEN_STORAGE_DIR / "upstox_token.json"
    CREDENTIALS_FILE = Path.home() / ".hft" / "credentials.json"
    
    # Logging
    LOG_LEVEL = "INFO"
    LOG_FILE = Path.home() / ".hft" / "logs" / "hft.log"
    
    def __init__(self, 
                 credentials: Optional[Credentials] = None,
                 token_storage_dir: Optional[Path] = None):
        """Initialize configuration.
        
        Args:
            credentials: Credentials object. If None, loads from env or file.
            token_storage_dir: Custom token storage directory.
        """
        self.credentials = credentials or self._load_credentials()
        
        if token_storage_dir:
            self.TOKEN_STORAGE_DIR = Path(token_storage_dir)
            self.TOKEN_FILE = self.TOKEN_STORAGE_DIR / "upstox_token.json"
    
    def _load_credentials(self) -> Credentials:
        """Load credentials from environment or file."""
        # Try environment variables first
        if all([
            os.getenv("UPSTOX_CLIENT_ID"),
            os.getenv("UPSTOX_CLIENT_SECRET")
        ]):
            return Credentials.from_env()
        
        # Try credentials file
        if self.CREDENTIALS_FILE.exists():
            return Credentials.from_file(str(self.CREDENTIALS_FILE))
        
        # Return empty credentials (will need to be set later)
        return Credentials("", "", "http://localhost:8080/callback")
    
    def ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        self.TOKEN_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        self.LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    def save_credentials(self) -> None:
        """Save current credentials to file."""
        self.ensure_directories()
        self.credentials.to_file(str(self.CREDENTIALS_FILE))
    
    def __repr__(self) -> str:
        return f"Config(credentials={self.credentials})"
