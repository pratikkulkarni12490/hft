"""Brokerage and charges estimation for NIFTY Futures trades."""

from dataclasses import dataclass


@dataclass
class TradeCharges:
    """Total charges for a complete trade (entry + exit)."""
    
    total: float = 0.0
    brokerage: float = 0.0
    stt: float = 0.0
    gst: float = 0.0
    transaction: float = 0.0
    stamp_duty: float = 0.0
    sebi: float = 0.0


class ChargesCalculator:
    """Estimates brokerage and charges for NIFTY Futures intraday trades.
    
    Based on typical charges:
    - Brokerage: ₹20 per order (Upstox flat fee)
    - STT: 0.0125% on sell side (futures)
    - Exchange Transaction: 0.002%
    - GST: 18% on (brokerage + transaction)
    - SEBI Turnover: 0.0001%
    - Stamp Duty: 0.003% on buy side
    """
    
    NIFTY_LOT_SIZE = 25
    
    def estimate(self, entry_price: float, exit_price: float, lots: int = 1) -> TradeCharges:
        """Estimate charges for a complete trade.
        
        Args:
            entry_price: Entry price.
            exit_price: Exit price.
            lots: Number of lots.
        
        Returns:
            TradeCharges with breakdown.
        """
        quantity = lots * self.NIFTY_LOT_SIZE
        entry_value = entry_price * quantity
        exit_value = exit_price * quantity
        turnover = entry_value + exit_value
        
        # Brokerage (₹20 per order × 2 orders)
        brokerage = 40.0
        
        # STT (0.0125% on sell side only for futures)
        stt = exit_value * 0.000125
        
        # Exchange Transaction (0.002% on turnover)
        transaction = turnover * 0.00002
        
        # GST (18% on brokerage + transaction)
        gst = (brokerage + transaction) * 0.18
        
        # SEBI Turnover (0.0001% on turnover)
        sebi = turnover * 0.000001
        
        # Stamp Duty (0.003% on buy side)
        stamp_duty = entry_value * 0.00003
        
        total = brokerage + stt + gst + transaction + sebi + stamp_duty
        
        return TradeCharges(
            total=round(total, 2),
            brokerage=round(brokerage, 2),
            stt=round(stt, 2),
            gst=round(gst, 2),
            transaction=round(transaction, 2),
            stamp_duty=round(stamp_duty, 2),
            sebi=round(sebi, 2)
        )
