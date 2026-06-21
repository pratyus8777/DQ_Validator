import json
import pandas as pd
from data_io.learning_store import LearningStore


class LocalLearningStore(LearningStore):
    """
    Stores learning artifacts locally.
    """

    def __init__(self, path: str):
        self.path = path
        self._load()

    def _load(self):
        try:
            with open(self.path, "r") as f:
                self.memory = json.load(f)
        except FileNotFoundError:
            self.memory = {"corrections": []}

    def apply_corrections(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        for item in self.memory.get("corrections", []):
            df.loc[
                df[item["cde"]] == item["old"],
                item["cde"]
            ] = item["new"]
        return df

    def persist_feedback(self, feedback: list):
        self.memory["corrections"].extend(feedback)
        with open(self.path, "w") as f:
            json.dump(self.memory, f, indent=2)
