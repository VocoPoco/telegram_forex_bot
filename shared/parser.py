from datetime import datetime
from models.signal import Signal
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
        Parses signals like:

            ENTRIAMO IN BUY SU XAUUSD
            ENTRATA <4207.5-4208.5>
            STOP LOSS 4160
            TAKE PROFIT 1 4214
            TAKE PROFIT 2 4215

        Returns: list[Signal]
        """

        lines = text.upper().splitlines()

        symbol = None
        direction = None
        entry_low = None
        entry_high = None
        sl_value = None
        tp_values = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if "BUY" in line:
                direction = "BUY"
            if "SELL" in line:
                direction = "SELL"

            if " SU " in line:
                parts = line.split()
                for p in parts:
                    if p.isalpha() and len(p) >= 4:
                        symbol = p + ".s"

            if line.startswith("ENTRATA"):
                cleaned = (
                    line.replace("ENTRATA", "")
                        .replace("<", "")
                        .replace(">", "")
                        .strip()
                )

                if "-" in cleaned:
                    left, right = cleaned.split("-", 1)
                    entry_low = self._normalize_number(left)
                    entry_high = self._normalize_number(right)
                    entry_low, entry_high = sorted([entry_low, entry_high])

            if "STOP LOSS" in line:
                parts = line.split()
                sl_value = self._normalize_number(parts[-1])

            if line.startswith("TAKE PROFIT"):
                parts = line.split()
                tp_values.append(self._normalize_number(parts[-1]))

        if not symbol or not direction or not entry_low or not entry_high or not sl_value:
            logger.error("Incomplete signal: %s", text)
            return None

        if not tp_values:
            logger.error("No TP values found: %s", text)
            return None

        signals = []
        for index, tp in enumerate(tp_values, start=1):
            signals.append(Signal(
                message_id=message_id,
                created_at=created_at,
                symbol=symbol,
                side=direction,
                entry_low=entry_low,
                entry_high=entry_high,
                tp=tp,
                sl=sl_value,
                raw_text=text,
                tp_index=index
            ))

        return signals