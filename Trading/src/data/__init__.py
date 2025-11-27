"""Data fetching module for Upstox API."""

import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import quote
from ..utils import Logger


NIFTY_INDEX_KEY = "NSE_INDEX|Nifty 50"


class CandleDataFetcher:
    """Fetches historical and intraday candle data from Upstox v3 API."""
    
    def __init__(self, auth_token: str):
        self.auth_token = auth_token
        self.base_url = "https://api.upstox.com/v3"
        self.logger = Logger.get()
        self.headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    def get_candles(self, instrument_key: str, interval: int = 5, unit: str = "minutes",
                    to_date: datetime = None, from_date: datetime = None) -> Optional[pd.DataFrame]:
        """Fetch historical candle data."""
        to_date = to_date or datetime.now() - timedelta(days=1)
        from_date = from_date or to_date - timedelta(days=30)
        
        encoded_key = quote(instrument_key, safe='')
        url = f"{self.base_url}/historical-candle/{encoded_key}/{unit}/{interval}/{to_date.strftime('%Y-%m-%d')}/{from_date.strftime('%Y-%m-%d')}"
        
        try:
            resp = requests.get(url, headers=self.headers, timeout=10)
            if resp.status_code != 200:
                self.logger.warning(f"Failed to fetch data for {instrument_key}: {resp.status_code} - {resp.text[:100]}")
                return None
            
            data = resp.json()
            candles = data.get("data", {}).get("candles", [])
            
            if not candles:
                return None
            
            df = pd.DataFrame(candles, columns=["timestamp", "open", "high", "low", "close", "volume", "oi"])
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            for col in ["open", "high", "low", "close", "volume", "oi"]:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            
            return df.sort_values("timestamp").reset_index(drop=True)
        
        except Exception as e:
            self.logger.error(f"Error fetching candles: {str(e)}")
            return None
    
    def get_nifty_index_candles(self, interval: int = 5, unit: str = "minutes",
                                 to_date: datetime = None, from_date: datetime = None) -> Optional[pd.DataFrame]:
        """Fetch NIFTY 50 Index candle data (handles chunking for large ranges)."""
        to_date = to_date or datetime.now() - timedelta(days=1)
        from_date = from_date or to_date - timedelta(days=7)
        
        total_days = (to_date - from_date).days
        
        # Chunk requests for minute data (API limit ~30 days)
        if unit == "minutes" and total_days > 30:
            all_dfs = []
            chunk_end = to_date
            
            while chunk_end > from_date:
                chunk_start = max(chunk_end - timedelta(days=30), from_date)
                df = self.get_candles(NIFTY_INDEX_KEY, interval, unit, chunk_end, chunk_start)
                if df is not None and len(df) > 0:
                    all_dfs.append(df)
                chunk_end = chunk_start - timedelta(days=1)
            
            if not all_dfs:
                return None
            
            combined = pd.concat(all_dfs, ignore_index=True)
            return combined.drop_duplicates(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
        
        return self.get_candles(NIFTY_INDEX_KEY, interval, unit, to_date, from_date)
    
    def get_nifty_intraday(self, interval: int = 5) -> Optional[pd.DataFrame]:
        """Fetch NIFTY 50 Index intraday candles for today."""
        encoded_key = quote(NIFTY_INDEX_KEY, safe='')
        
        # Try v2 API first (more reliable for intraday)
        url = f"https://api.upstox.com/v2/market-quote/ohlc?instrument_key={encoded_key}&interval={interval}minute"
        
        try:
            resp = requests.get(url, headers=self.headers, timeout=10)
            self.logger.debug(f"Intraday API response: {resp.status_code}")
            
            if resp.status_code == 404:
                # Fallback: Use historical data for today
                self.logger.info("Intraday API not available, using historical data")
                today = datetime.now()
                return self.get_candles(NIFTY_INDEX_KEY, interval, "minutes", today, today - timedelta(days=1))
            
            if resp.status_code != 200:
                self.logger.warning(f"Failed to fetch intraday data: {resp.status_code} - {resp.text[:200]}")
                # Fallback to historical
                today = datetime.now()
                return self.get_candles(NIFTY_INDEX_KEY, interval, "minutes", today, today - timedelta(days=1))
            
            data = resp.json()
            candles = data.get("data", {}).get("candles", [])
            
            if not candles:
                # Fallback to historical
                self.logger.info("No intraday candles, using historical data")
                today = datetime.now()
                return self.get_candles(NIFTY_INDEX_KEY, interval, "minutes", today, today - timedelta(days=1))
            
            df = pd.DataFrame(candles, columns=["timestamp", "open", "high", "low", "close", "volume", "oi"])
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            for col in ["open", "high", "low", "close", "volume", "oi"]:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            
            return df.sort_values("timestamp").reset_index(drop=True)
        
        except Exception as e:
            self.logger.error(f"Error fetching intraday: {str(e)}")
            # Fallback to historical
            today = datetime.now()
            return self.get_candles(NIFTY_INDEX_KEY, interval, "minutes", today, today - timedelta(days=1))


