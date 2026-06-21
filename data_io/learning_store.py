from abc import ABC, abstractmethod
import pandas as pd


class LearningStore(ABC):
    """
    Abstract interface for storing and applying learning.
    """

    @abstractmethod
    def apply_corrections(self, df: pd.DataFrame) -> pd.DataFrame:
        pass

    @abstractmethod
    def persist_feedback(self, feedback: list):
        pass
