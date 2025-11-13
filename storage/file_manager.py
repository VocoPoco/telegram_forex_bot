import json
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from shared.constants import LAST_MESSAGE_ID_PATH, HISTORY_PATH, RESULTS_PATH
import logging

# module-level logger
logger = logging.getLogger(__name__)


class FileManager:
    """
    Handles reading, writing, and appending files for message IDs,
    signal histories, and evaluation results.
    Keeps all file I/O in one place.
    """

    def __init__(
        self,
        LAST_MESSAGE_ID_PATH: str = LAST_MESSAGE_ID_PATH,
        history_path: str = HISTORY_PATH,
        results_path: str = RESULTS_PATH
    ):
        self.LAST_MESSAGE_ID_PATH = Path(LAST_MESSAGE_ID_PATH)
        self.history_path = Path(history_path)
        self.results_path = Path(results_path)

        logger.info(
            "FileManager initialized with paths: last_message_id=%s, history=%s, results=%s",
            self.LAST_MESSAGE_ID_PATH, self.history_path, self.results_path
        )

    def read_last_message_id(self) -> Optional[int]:
        """Read the last saved message ID from file."""
        if not self.LAST_MESSAGE_ID_PATH.exists():
            logger.warning("Last message ID file does not exist: %s", self.LAST_MESSAGE_ID_PATH)
            return None

        try:
            value = int(self.LAST_MESSAGE_ID_PATH.read_text().strip())
            logger.info("Read last message ID: %s", value)
            return value
        except Exception:
            logger.exception("Failed to read last message ID from %s", self.LAST_MESSAGE_ID_PATH)
            return None

    def write_last_message_id(self, message_id: int) -> None:
        """Write the last processed message ID to file."""
        try:
            self.LAST_MESSAGE_ID_PATH.parent.mkdir(parents=True, exist_ok=True)
            self.LAST_MESSAGE_ID_PATH.write_text(str(message_id))
            logger.info("Saved last message ID: %s", message_id)
        except Exception:
            logger.exception("Failed to write last message ID to %s", self.LAST_MESSAGE_ID_PATH)

    def save_json(self, obj: Any, path: Optional[str] = None) -> None:
        """Save an object as formatted JSON."""
        target = Path(path or self.history_path)
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(obj, default=str, indent=2))
            logger.info("Saved JSON to %s", target)
        except Exception:
            logger.exception("Failed to save JSON to %s", target)

    def load_json(self, path: Optional[str] = None) -> Any:
        """Load a JSON file into memory."""
        target = Path(path or self.history_path)

        if not target.exists():
            logger.warning("JSON file does not exist: %s", target)
            return None

        try:
            data = json.loads(target.read_text())
            logger.info("Loaded JSON from %s", target)
            return data
        except Exception:
            logger.exception("Failed to load JSON from %s", target)
            return None

    def save_results_to_json(self, rows: list[dict], path: Optional[str] = None) -> None:
        """
        Overwrite (rewrite) a .jsonl file with new rows.
        Each row is written on a new line for structured, easy-to-read storage.
        Existing data will be replaced.
        """
        target = Path(path or self.results_path)

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("w", encoding="utf-8") as f:
                for r in rows:
                    f.write(json.dumps(r, default=str) + "\n")

            logger.info("Saved %d result rows to JSONL %s", len(rows), target)

        except Exception:
            logger.exception("Failed to save results JSONL to %s", target)

    def save_results_to_excel(self, rows: list[dict], folder: str = "output", filename: str = "signal_results.xlsx"):
        """Save results to an Excel file for easier analysis."""
        output_dir = Path(folder)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / filename

        try:
            for row in rows:
                for key, value in row.items():
                    if isinstance(value, datetime):
                        row[key] = value.replace(tzinfo=None)

            df = pd.DataFrame(rows)
            df.to_excel(output_path, index=False)

            logger.info("Saved results to Excel: %s", output_path)

        except Exception:
            logger.exception("Failed to save results to Excel at %s", output_path)
