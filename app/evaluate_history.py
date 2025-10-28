from datetime import datetime, timezone
from storage.file_manager import FileManager
from shared.parser import SignalParser
from mt_bot.mt5_client import MT5Client
from mt_bot.evaluator import Evaluator
from shared.constants import MT5_ACCOUNT, MT5_PASSWORD, MT5_SERVER

if __name__ == "__main__":
    file_manager = FileManager()
    parser = SignalParser()
    raw = file_manager.load_json("var/messages_since_date.json")
    

    mt5 = MT5Client(MT5_ACCOUNT, MT5_PASSWORD, MT5_SERVER)
    mt5.connect()
    evaluator = Evaluator(mt5)

    rows = []
    for r in raw:
        sig = parser.parse(r["id"], r["date"], r["text"])
        if not sig:
            continue
        res = evaluator.evaluate_signal(sig)
        rows.append({
            "message_id": sig.message_id,
            "symbol": sig.symbol,
            "side": sig.side,
            "tp": sig.tp,
            "sl": sig.sl,
            "hit": res.hit,
            "hit_time": res.hit_time,
            "entry_type": res.entry_type,
            "notes": res.notes,
        })

    file_manager.append_results(rows)
    mt5.shutdown()
    print(f"Wrote {len(rows)} results to var/signal_results.jsonl")
