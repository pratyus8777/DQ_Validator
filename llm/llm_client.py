import logging
import requests
import time

logger = logging.getLogger(__name__)


class LLMClient:
    """
    Thin, safe wrapper around any LLM provider.
    Supports Ollama and other providers.
    """

    def __init__(self, config: dict):
        self.enabled = config.get("enabled", False)
        self.provider = config.get("provider", "ollama")
        self.model = config.get("model", "llama2")
        # default timeout per call (seconds)
        self.timeout = config.get("timeout", 30)
        self.fast_timeout = config.get("fast_timeout", 3)  # Quick timeout for simple rules
        self.max_attempts = config.get("max_attempts", config.get("max_llm_attempts", 1))
        self.base_url = config.get("base_url", "http://localhost:11434")
        self._available = None

    @property
    def available(self) -> bool:
        """Check if LLM service is available."""
        if self._available is None:
            self._available = self._check_availability()
        return self._available

    def _check_availability(self) -> bool:
        """Check if the LLM service is reachable."""
        if not self.enabled:
            return False
        try:
            if self.provider == "ollama":
                response = requests.get(f"{self.base_url}/api/tags", timeout=5)
                return response.status_code == 200
            return True
        except Exception as e:
            logger.warning(f"LLM service unavailable: {e}")
            return False

    def is_complex_rule(self, text: str) -> bool:
        """Detect if rule requires LLM consultation (vs fast heuristic).
        Complex rules: conditional logic, multiple operations, domain-specific requirements"""
        complex_keywords = [
            'if ', 'conditional', 'based on', 'depends on',
            'calculate', 'aggregate', 'sum', 'average', 'count',
            'lookup', 'reference', 'join', 'merge',
            'mapping', 'mapping table',
            'validation rule', 'validation',
            'custom logic', 'complex',
            'when ', 'then ',
        ]
        text_lower = text.lower().strip()
        return any(kw in text_lower for kw in complex_keywords)

    def complete(self, prompt: str, timeout: int | None = None, force_llm: bool = False) -> str | None:
        """
        Returns LLM output or None if disabled/fails.
        force_llm=True: Wait longer for LLM (for complex rules)
        timeout override available for specific needs
        """
        if not self.enabled:
            return None

        if not self.available:
            logger.debug(f"LLM service not available (provider: {self.provider})")
            return None

        # Auto-detect timeout based on rule complexity
        if timeout is None:
            if force_llm or self.is_complex_rule(prompt):
                timeout = self.timeout  # Wait longer (5s) for complex rules
            else:
                timeout = self.fast_timeout  # Quick check (3s) for simple rules

        try:
            if self.provider == "ollama":
                return self._call_ollama(prompt, timeout=timeout)
            else:
                logger.warning(f"Unknown provider: {self.provider}")
                return None
        except Exception as e:
            logger.error(f"Error calling LLM: {e}")
            return None

    def _call_ollama(self, prompt: str, timeout: int | None = None) -> str | None:
        """Call Ollama API with fast timeout - fail fast, fallback to heuristics."""
        call_timeout = timeout if timeout is not None else self.timeout
        max_attempts = self.max_attempts
        
        for attempt in range(1, max_attempts + 1):
            try:
                response = requests.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False
                    },
                    timeout=call_timeout
                )
                response.raise_for_status()
                result = response.json()
                return result.get("response", "")
            except requests.exceptions.Timeout:
                logger.debug(f"LLM timeout ({call_timeout}s) - will use heuristics")
                return None  # Fail fast, don't retry
            except requests.exceptions.RequestException as e:
                logger.debug(f"LLM failed: {e} - will use heuristics")
                return None  # Fail fast
