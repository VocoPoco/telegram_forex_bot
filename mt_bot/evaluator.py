from datetime import datetime, timedelta, timezone
from models.signal import Signal
from models.evaluation_result import EvaluationResult
import MetaTrader5 as mt5


class Evaluator:
    """
    Evaluates whether a given trading signal would have hit TP or SL first.
    Steps:
      1. Determine entry type (MARKET, LIMIT, STOP) and entry price.
      2. Walk forward bar-by-bar until TP or SL is touched.
      3. Handle tie cases using tick data for precision.
    """

    def __init__(self, mt5_client):
        self.mt5 = mt5_client


    def decide_entry(self, symbol: str, side: str, entry_low: float, entry_high: float) -> tuple[str, float | None]:
        """Determine entry type and entry price based on the signal and current market price."""
        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            return "MARKET", None

        ask, bid = tick.ask, tick.bid
        side = side.upper()

        if side == "BUY":
            if entry_low > ask:
                return "BUY_STOP", entry_low
            if entry_high < ask:
                return "BUY_LIMIT", entry_high
            return "MARKET", ask
        else:
            if entry_high < bid:
                return "SELL_STOP", entry_high
            if entry_low > bid:
                return "SELL_LIMIT", entry_low
            return "MARKET", bid

  
    def evaluate_signal(self, signal: Signal, timeout_minutes: int = 48 * 60) -> dict:
        """
        Evaluate a signal and return a result dict:
        {
            'status': 'TP' | 'SL' | None,
            'hit_time': datetime | None,
            'entry_type': str,
            'notes': str
        }
        """
        self.mt5.ensure_symbol(signal.symbol)

        entry_type, entry_price = self.decide_entry(signal.symbol, signal.side, signal.entry_low, signal.entry_high)
        if isinstance(signal.created_at, str):
            signal.created_at = datetime.fromisoformat(signal.created_at.replace("Z", "+00:00"))

        evaluation_start = signal.created_at
        evaluation_end = signal.created_at + timedelta(minutes=timeout_minutes)

        bars = self.mt5.get_bars(signal.symbol, mt5.TIMEFRAME_M1, evaluation_start, evaluation_end)
        bars = bars if bars is not None else []

        if len(bars) == 0:  
            return self._make_result(None, None, None, entry_type, "no bars")

        in_trade = entry_type == "MARKET"

        for bar in bars:
            result = self._evaluate_bar(signal, bar, in_trade, entry_type, entry_price)
            if result:
                return result
            if not in_trade and entry_price:
                in_trade = self._check_entry_trigger(signal, bar, entry_price)
        return self._make_result(None, entry_price, None, entry_type, "timeout")


    def _evaluate_bar(self, signal: Signal, bar, in_trade: bool, entry_type: str, entry_price: float | None) -> dict | None:
        """Check one M1 bar to see if TP or SL was hit."""
        side = signal.side.upper()
        bar_time = datetime.fromtimestamp(bar['time'])
        bar_high, bar_low = bar['high'], bar['low']

        if not in_trade:
            return None 

        tp_hit = (bar_high >= signal.tp) if side == "BUY" else (bar_low <= signal.tp)
        sl_hit = (bar_low <= signal.sl) if side == "BUY" else (bar_high >= signal.sl)

        if tp_hit:
            return self._make_result("TP", entry_price, bar_time , entry_type, signal.tp - entry_price if side == "BUY" else entry_price - signal.tp) 

        if sl_hit:
            return self._make_result("SL", entry_price, bar_time, entry_type, signal.sl - entry_price if side == "BUY"else entry_price - signal.sl )

        return None


    def _check_entry_trigger(self, signal: Signal, bar, entry_price: float) -> bool:
        """Check if entry conditions were met within the bar."""
        side = signal.side.upper()
        bar_high, bar_low = bar['high'], bar['low']
        if side == "BUY" and bar_high >= entry_price:
            return True
        if side == "SELL" and bar_low <= entry_price:
            return True
        return False

  
    def _make_result(self, status: str | None, entry_price: float | None, hit_time: datetime | None, entry_type: str, profit: float, notes: str = "") -> dict:
        """Return standardized evaluation result as dict."""
        return EvaluationResult(status, hit_time, entry_price, entry_type, notes, profit)
    
    
    def calculate_sucess_rate(self, results: list) -> float:
        """Calculate the success rate (TP hits) from a list of evaluation results."""
        if not results:
            return 0.0
        
        def _get_status(res):
            if isinstance(res, dict):
                return res.get("status")
            return getattr(res, "status", None)

        tp_hits = 0
        valid_count = 0

        for res in results:
            status = _get_status(res)
            if status is None:
                continue       
            valid_count += 1
            if status == "TP":
                tp_hits += 1

        if valid_count == 0:
            return 0.0

        return tp_hits / valid_count