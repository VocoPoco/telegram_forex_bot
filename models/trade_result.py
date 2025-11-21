from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class TradeResult:
    success: bool
    order_id: Optional[int]
    deal_id: Optional[int]
    price: Optional[float]
    comment: str
    executed_at: datetime