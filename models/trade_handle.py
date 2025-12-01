from dataclasses import dataclass
from datetime import datetime
from models.signal import Signal

@dataclass
class TradeHandle:
    ticket: int                   
    signal: Signal               
    signal_entry_price: float
    executed_price: float          
    opened_at: datetime
    market_price_at_signal: float
    pending_order_ticket: int | None = None 