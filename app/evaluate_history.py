from datetime import datetime, timezone
from storage.file_manager import FileManager
from shared.parser import SignalParser
from mt_bot.mt5_client import MT5Client
from mt_bot.evaluator import Evaluator
from shared.constants import MT5_ACCOUNT_DEMO, MT5_PASSWORD_DEMO, MT5_SERVER_DEMO

if __name__ == "__main__":
    file_manager = FileManager()
    parser = SignalParser()
    raw = file_manager.load_json("var/messages_since_date.json")

    with MT5Client(MT5_ACCOUNT_DEMO, MT5_PASSWORD_DEMO, MT5_SERVER_DEMO) as mt5:
        evaluator = Evaluator(mt5)
        rows = []

        for part in raw:
            sig = parser.parse(part["id"], part["date"], part["text"])
            if not sig:
                continue

            res = evaluator.evaluate_signal(sig)
            print(f"Evaluated message {sig.message_id}")

            rows.append({
                "message_id": sig.message_id,
                "symbol": sig.symbol,
                "side": sig.side,
                "entry_price": getattr(res, "entry_price"),
                "tp": sig.tp,
                "sl": sig.sl,
                "created_at": sig.created_at,
                "hit_time": getattr(res, "hit_time"),
                "entry_type": getattr(res, "entry_type"),
                "status": getattr(res, "status"), 
                "profit": getattr(res, "profit", ""),
                "notes": getattr(res, "notes", ""),
            })
        file_manager.save_results_to_json(rows)
        file_manager.save_results_to_excel(rows, folder="output")

        print(f"Wrote {len(rows)} results to output folder.")
        print(evaluator.calculate_sucess_rate(rows))
