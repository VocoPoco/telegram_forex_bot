from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Signal:
    message_id: int
    created_at: datetime
    symbol: str
    side: str 
    entry_low: float
    entry_high: float
    tp: float
    sl: float
    raw_text: str

@dataclass
class TradeResult:
    success: bool
    order_id: Optional[int]
    deal_id: Optional[int]
    price: Optional[float]
    comment: str
    executed_at: datetime