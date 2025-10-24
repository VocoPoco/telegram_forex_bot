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
class SignalResult:
    signal: Signal
    hit: Optional[str]
    hit_time: Optional[datetime]
    entry_type: str 
    notes: str = ""
