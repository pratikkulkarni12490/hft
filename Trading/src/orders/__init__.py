"""Order placement module for live trading with Upstox API."""

import requests
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict
from enum import Enum
from ..utils import Logger


class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    SL_M = "SL-M"  # Stop Loss Market


class TransactionType(Enum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass
class OrderResponse:
    """Response from order placement."""
    success: bool
    order_id: Optional[str] = None
    message: str = ""


class OrderPlacer:
    """Places orders via Upstox API. Supports paper trading mode."""
    
    NIFTY_LOT_SIZE = 25
    ORDER_URL = "https://api-hft.upstox.com/v2/order/place"
    
    def __init__(self, auth_token: str, paper_trading: bool = True):
        self.auth_token = auth_token
        self.paper_trading = paper_trading
        self.logger = Logger.get()
        self.headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        self.paper_trades = []
        self._order_counter = 0
    
    def place_order(self, instrument_token: str, quantity: int, 
                    txn_type: TransactionType, order_type: OrderType,
                    price: float = 0.0, trigger_price: float = 0.0) -> OrderResponse:
        """Place an order (paper or live)."""
        
        if self.paper_trading:
            self._order_counter += 1
            order_id = f"PAPER_{datetime.now().strftime('%Y%m%d%H%M%S')}_{self._order_counter}"
            
            self.paper_trades.append({
                "order_id": order_id,
                "timestamp": datetime.now().isoformat(),
                "instrument_token": instrument_token,
                "quantity": quantity,
                "transaction_type": txn_type.value,
                "order_type": order_type.value,
                "price": price,
                "trigger_price": trigger_price
            })
            
            self.logger.info(f"[PAPER] {txn_type.value} {quantity} @ {order_type.value}")
            return OrderResponse(success=True, order_id=order_id, message="Paper order placed")
        
        # Live order
        try:
            payload = {
                "instrument_token": instrument_token,
                "quantity": quantity,
                "transaction_type": txn_type.value,
                "order_type": order_type.value,
                "product": "I",  # Intraday
                "price": price,
                "trigger_price": trigger_price,
                "validity": "DAY",
                "disclosed_quantity": 0,
                "is_amo": False
            }
            
            resp = requests.post(self.ORDER_URL, headers=self.headers, json=payload, timeout=10)
            data = resp.json()
            
            if resp.status_code == 200 and data.get("status") == "success":
                order_id = data.get("data", {}).get("order_id")
                self.logger.info(f"[LIVE] Order placed: {order_id}")
                return OrderResponse(success=True, order_id=order_id)
            else:
                self.logger.error(f"[LIVE] Order failed: {data}")
                return OrderResponse(success=False, message=str(data))
        
        except Exception as e:
            self.logger.error(f"Order error: {str(e)}")
            return OrderResponse(success=False, message=str(e))
    
    def place_bracket_order(self, instrument_token: str, lots: int,
                            entry_price: float, stop_loss: float, 
                            take_profit: float) -> Dict[str, OrderResponse]:
        """Place entry + SL + TP orders."""
        quantity = lots * self.NIFTY_LOT_SIZE
        results = {}
        
        # Entry (market order)
        results["entry"] = self.place_order(
            instrument_token, quantity, TransactionType.BUY, OrderType.MARKET
        )
        
        if not results["entry"].success:
            return results
        
        # Stop Loss (SL-M order)
        results["stop_loss"] = self.place_order(
            instrument_token, quantity, TransactionType.SELL, OrderType.SL_M,
            trigger_price=stop_loss
        )
        
        # Take Profit (limit order)
        results["take_profit"] = self.place_order(
            instrument_token, quantity, TransactionType.SELL, OrderType.LIMIT,
            price=take_profit
        )
        
        return results


# Current NIFTY Futures contract
NIFTY_FUTURES = "NSE_FO|NIFTY25DECFUT"
