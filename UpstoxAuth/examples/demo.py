#!/usr/bin/env python3
"""
Demo script to run Upstox authentication flow and print token status.
"""
import sys
from pathlib import Path

# Add UpstoxAuth module to path
upstoxauth_dir = Path(__file__).parent.parent
sys.path.insert(0, str(upstoxauth_dir))

from src.config import Credentials
from src.auth import UpstoxAuthenticator


def main():
    print("\n=== Upstox Authentication Demo ===\n")
    authenticator = UpstoxAuthenticator()
    if authenticator.is_authenticated():
        print("✓ Already authenticated!")
        print(f"Token: {authenticator.get_token()}")
        print(f"Status: {authenticator.get_status()}")
    else:
        print("Not authenticated. Starting authentication flow...")
        if len(sys.argv) > 1:
            auth_code = sys.argv[1]
            token = authenticator.authenticate(auth_code)
            if token:
                print("✓ Authentication successful!")
                print(f"Token: {token}")
                print(f"Status: {authenticator.get_status()}")
            else:
                print("✗ Authentication failed.")
        else:
            print("✗ No auth_code provided. Please run as: python demo.py <auth_code>")

if __name__ == "__main__":
    main()
