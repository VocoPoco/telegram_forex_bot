from dataclasses import dataclass, field
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
    pending_order_tickets: list[int] = field(default_factory=list)
    is_parent: bool = False              
