from datetime import datetime
from dataclasses import dataclass

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
    tp_index: int