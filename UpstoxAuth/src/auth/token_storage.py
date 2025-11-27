"""Token storage and persistence module."""

import json
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from ..utils import Logger, TimeUtils


@dataclass
class TokenData:
    """Represents stored token information."""
    
    access_token: str
    user_id: str
    user_name: str
    email: str
    broker: str
    issued_at: str  # ISO format datetime
    expires_at: str  # ISO format datetime
    exchanges: list = field(default_factory=list)
    products: list = field(default_factory=list)
    order_types: list = field(default_factory=list)
    extended_token: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TokenData":
        """Create from dictionary."""
        return cls(**data)
    
    def is_expired(self) -> bool:
        """Check if token is expired."""
        issued = datetime.fromisoformat(self.issued_at)
        return TimeUtils.is_token_expired(issued)
    
    def get_expiry_datetime(self) -> datetime:
        """Get expiry datetime object."""
        return datetime.fromisoformat(self.expires_at)
    
    def get_issued_datetime(self) -> datetime:
        """Get issued datetime object."""
        return datetime.fromisoformat(self.issued_at)
    
    def __str__(self) -> str:
        """String representation."""
        return (
            f"TokenData(user={self.user_name}, "
            f"access_token='{self.access_token[:20]}...', "
            f"expires={self.expires_at})"
        )


class TokenStorage:
    """Manages token persistence and retrieval."""
    
    def __init__(self, storage_path: Path):
        """Initialize token storage.
        
        Args:
            storage_path: Path to store token file.
        """
        self.storage_path = Path(storage_path)
        self.logger = Logger.get()
    
    def ensure_directory(self) -> None:
        """Ensure storage directory exists."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
    
    def save_token(self, token_data: TokenData) -> bool:
        """Save token to storage.
        
        Args:
            token_data: TokenData object to save.
        
        Returns:
            True if successful, False otherwise.
        """
        try:
            self.ensure_directory()
            with open(self.storage_path, 'w') as f:
                json.dump(token_data.to_dict(), f, indent=2)
            return True
        except Exception as e:
            self.logger.error(f"Failed to save token: {str(e)}")
            return False
    
    def load_token(self) -> Optional[TokenData]:
        """Load token from storage.
        
        Returns:
            TokenData if exists and valid, None otherwise.
        """
        try:
            if not self.storage_path.exists():
                self.logger.debug(f"Token file not found: {self.storage_path}")
                return None
            
            with open(self.storage_path, 'r') as f:
                data = json.load(f)
            
            token_data = TokenData.from_dict(data)
            return token_data
        except Exception as e:
            self.logger.error(f"Failed to load token: {str(e)}")
            return None
    
    def delete_token(self) -> bool:
        """Delete stored token.
        
        Returns:
            True if successful or file doesn't exist, False on error.
        """
        try:
            if self.storage_path.exists():
                self.storage_path.unlink()
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete token: {str(e)}")
            return False
    
    def get_valid_token(self) -> Optional[TokenData]:
        """Get valid (non-expired) token from storage.
        
        Returns:
            TokenData if exists and not expired, None otherwise.
        """
        token_data = self.load_token()
        
        if token_data is None:
            return None
        
        if token_data.is_expired():
            return None
        
        return token_data
    
    def clear(self) -> bool:
        """Clear all stored tokens."""
        return self.delete_token()
