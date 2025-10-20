def normalize_number(s: str) -> float:
    """
    Convert a string into a float, replacing commas with dots and trimming spaces.
    """
    return float(s.replace(",", ".").strip())


def parse_signal(text: str):
    """
    Parse a trading signal in the format:
    SYMBOL SIDE (ENTRY_LOW-ENTRY_HIGH)
    TP TP_VALUE 
    STOP LOSS: SL_VALUE

    Splits the message and extracts symbol, side, entry range, TP, and SL.
    Returns a dictionary with these values or None if parsing fails.
    """
    text = text.strip().upper().replace("\n", " ")

    try:
        parts = text.split()

        side   = parts[1]      

        entry_str = parts[2].strip("()") 
        entry_low, entry_high = map(normalize_number, entry_str.split("-"))

        tp_index = parts.index("TP")
        tp = normalize_number(parts[tp_index + 1])

        sl_index = parts.index("LOSS:")
        sl = normalize_number(parts[sl_index + 1])

        return {
            "side": side,
            "entry_low": entry_low,
            "entry_high": entry_high,
            "tp": tp,
            "sl": sl
        }
    except Exception as e:
        print(f"[Parser ERROR] Could not parse: {text} | {e}")
        return None
