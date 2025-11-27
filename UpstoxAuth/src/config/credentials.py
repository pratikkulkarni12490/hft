"""Credentials management for Upstox API authentication."""

import os
import json
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
from pathlib import Path


@dataclass
class Credentials:
    """Represents Upstox API credentials."""
    
    client_id: str
    client_secret: str
    redirect_uri: str
    
    def to_dict(self) -> Dict[str, str]:
        """Convert credentials to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> "Credentials":
        """Create credentials from dictionary."""
        return cls(**data)
    
    @classmethod
    def from_env(cls) -> "Credentials":
        """Load credentials from environment variables.
        
        Set the following environment variables:
        - UPSTOX_CLIENT_ID: Your Upstox API client ID
        - UPSTOX_CLIENT_SECRET: Your Upstox API client secret
        - UPSTOX_REDIRECT_URI: Your redirect URI (default: http://localhost)
        """
        return cls(
            client_id=os.getenv("UPSTOX_CLIENT_ID", ""),
            client_secret=os.getenv("UPSTOX_CLIENT_SECRET", ""),
            redirect_uri=os.getenv("UPSTOX_REDIRECT_URI", "http://localhost")
        )
    
    @classmethod
    def from_file(cls, filepath: str) -> "Credentials":
        """Load credentials from JSON file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)
    
    def to_file(self, filepath: str) -> None:
        """Save credentials to JSON file."""
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    def validate(self) -> bool:
        """Validate that all required credentials are present."""
        return all([self.client_id, self.client_secret, self.redirect_uri])
    
    def __str__(self) -> str:
        """String representation (hides sensitive data)."""
        return (
            f"Credentials(client_id='{self.client_id[:8]}...', "
            f"redirect_uri='{self.redirect_uri}')"
        )
