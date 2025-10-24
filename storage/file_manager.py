import json
from pathlib import Path
from typing import Any, Optional
from shared.constants import LAST_ID_PATH, HISTORY_PATH, RESULTS_PATH


class FileManager:
    """
    Handles reading, writing, and appending files for message IDs,
    signal histories, and evaluation results.
    Keeps all file I/O in one place.
    """

    def __init__(self, last_id_path: str = LAST_ID_PATH,
                 history_path: str = HISTORY_PATH,
                 results_path: str = RESULTS_PATH):
        self.last_id_path = Path(last_id_path)
        self.history_path = Path(history_path)
        self.results_path = Path(results_path)


    def read_last_message_id(self) -> Optional[int]:
        """Read the last saved message ID from file."""
        if not self.last_id_path.exists():
            return None
        try:
            return int(self.last_id_path.read_text().strip())
        except Exception:
            return None

    def write_last_message_id(self, message_id: int) -> None:
        """Write the last processed message ID to file."""
        self.last_id_path.parent.mkdir(parents=True, exist_ok=True)
        self.last_id_path.write_text(str(message_id))


    def save_json(self, obj: Any, path: Optional[str] = None) -> None:
        """Save an object as formatted JSON."""
        target = Path(path or self.history_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(obj, default=str, indent=2))

    def load_json(self, path: Optional[str] = None) -> Any:
        """Load a JSON file into memory."""
        target = Path(path or self.history_path)
        if not target.exists():
            return None
        return json.loads(target.read_text())


    def append_results(self, rows: list[dict], path: Optional[str] = None) -> None:
        """
        Append rows to a .jsonl (JSON lines) file.
        Each row is written on a new line for efficient incremental storage.
        """
        target = Path(path or self.results_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, default=str) + "\n")
