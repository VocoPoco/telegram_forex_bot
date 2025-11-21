from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class EvaluationResult:
    status: Optional[str]
    hit_time: Optional[datetime]
    entry_price: Optional[float]
    entry_type: str
    notes: str
    profit: Optional[float]