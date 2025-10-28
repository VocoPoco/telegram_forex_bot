from datetime import datetime
from domain.models import Signal


class SignalParser:
    """
    Parses raw Telegram message text into structured trading signals.
    Each parser instance can be configured (e.g., logging, normalization rules).
    """

    def __init__(self, normalize_commas: bool = True):
        self.normalize_commas = normalize_commas

    def _normalize_number(self, s: str) -> float:
        """Convert a string into a float, replacing commas with dots if configured."""
        if self.normalize_commas:
            s = s.replace(",", ".")
        return float(s.strip())

    def parse(self, message_id: int, created_at: datetime, text: str) -> Signal | None:
        """
        Converts a Telegram message like:
            "XAUUSD BUY (4276.5-4275.5) TP 4283 STOP LOSS: 4220"
        into a structured Signal object.
        """

        text_clean = text.strip().upper().replace("\n", " ")

        try:
            words = text_clean.split()

            # symbol = words[0] # Currently hardcoded to XAUUSD.s
            direction = words[1] 

            entry_range = words[2].strip("()").split("-")
            entry_low = self._normalize_number(entry_range[0])
            entry_high = self._normalize_number(entry_range[1])

            tp_value = self._normalize_number(words[words.index("TP") + 1])
            sl_value = self._normalize_number(words[words.index("LOSS:") + 1])

            return Signal(
                message_id=message_id,
                created_at=created_at,
                symbol="XAUUSD.s",
                side=direction,
                entry_low=entry_low,
                entry_high=entry_high,
                tp=tp_value,
                sl=sl_value,
                raw_text=text
            )

        except Exception as e:
            print(f"[Parser ERROR] Failed to parse message: {text} | Error: {e}")
            return None