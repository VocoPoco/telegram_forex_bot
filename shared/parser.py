from datetime import datetime
from domain.models import Signal
import logging

logger = logging.getLogger(__name__)


class SignalParser:
    """
    Parses raw Telegram message text into structured trading signals.
    """

    def __init__(self, normalize_commas: bool = True):
        self.normalize_commas = normalize_commas
        logger.info("SignalParser initialized (normalize_commas=%s)", normalize_commas)

    def _normalize_number(self, s: str) -> float:
        """Parse messy numeric strings without regex (handles extra dots/commas, junk chars)."""
        string = str(s)

        if self.normalize_commas:
            string = string.replace(",", ".")

        string = string.strip()
        out = []
        dot_seen = False
        minus_allowed = True

        for character in string:
            if character.isdigit():
                out.append(character)
                minus_allowed = False
            elif character == '.':
                if not dot_seen:
                    out.append('.')
                    dot_seen = True
                minus_allowed = False
            elif character == '-':
                if minus_allowed:
                    out.append('-')
                    minus_allowed = False
            else:
                continue

        cleaned = ''.join(out)

        if cleaned.endswith('.'):
            cleaned = cleaned[:-1]
        if cleaned in ('', '-'):
            raise ValueError(f"Cannot parse numeric value from '{s}'")

        return float(cleaned)

    def parse(self, message_id: int, created_at: datetime, text: str) -> Signal | None:
        """
        Converts a Telegram message like:
            "XAUUSD BUY (4276.5-4275.5) TP 4283 STOP LOSS: 4220"
        into a structured Signal object.

        Returns an instance of Signal or None if parsing fails.
        """

        text_clean = text.strip().upper().replace("\n", " ")

        try:
            words = text_clean.split()

            symbol = words[0]
            direction = words[1]

            entry_range = words[2].strip("()").split("-")
            entry_low = self._normalize_number(entry_range[0])
            entry_high = self._normalize_number(entry_range[1])

            entry_low, entry_high = sorted([entry_low, entry_high])

            tp_value = self._normalize_number(words[words.index("TP") + 1])
            sl_value = self._normalize_number(words[words.index("LOSS:") + 1])

            signal = Signal(
                message_id=message_id,
                created_at=created_at,
                symbol=symbol + ".s",
                side=direction,
                entry_low=entry_low,
                entry_high=entry_high,
                tp=tp_value,
                sl=sl_value,
                raw_text=text
            )

            logger.info("Parsed signal: %s", signal)
            return signal

        except Exception:
            logger.exception("Failed to parse message: %s", text)
            return None
