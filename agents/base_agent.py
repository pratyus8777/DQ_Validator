from abc import ABC, abstractmethod


class BaseAgent(ABC):
    """
    Base class for all agents (DQ, remediation, HITL, reporting).
    """

    def __init__(self, llm_client=None, config=None):
        self.llm = llm_client
        self.config = config or {}

    @abstractmethod
    def run(self, context: dict) -> dict:
        pass
