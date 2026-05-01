import json
import re
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class RegistryParser:
    """
    Utility class to parse raw tool outputs (JSON, HTML, Text) into agent-readable formats.
    """

    @staticmethod
    def parse_json(raw_data: str) -> Dict[str, Any]:
        """
        Parses JSON string, handling potential malformed data or empty strings.
        """
        if not raw_data or not raw_data.strip():
            return {}
        try:
            return json.loads(raw_data)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            # Attempt a partial recovery if possible (e.g., stripping markdown code blocks)
            clean_data = re.sub(r"```json\n|\n```", "", raw_data).strip()
            try:
                return json.loads(clean_data)
            except json.JSONDecodeError:
                return {"error": "malformed_json", "raw": raw_data[:500]}

    @staticmethod
    def parse_html_to_text(html_content: str) -> str:
        """
        Simplified HTML to text converter. Handles non-Latin characters and large documents.
        """
        if not html_content:
            return ""
        
        # Remove scripts and styles
        text = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        # Remove tags
        text = re.sub(r'<[^>]+>', ' ', text)
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text

    @staticmethod
    def sanitize_registry_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ensures registry data is cleaned, handling empty fields and non-Latin characters.
        """
        if not data:
            return {}

        def clean_value(v):
            if v is None:
                return ""
            if isinstance(v, str):
                # Ensure it's valid UTF-8 and strip whitespace
                try:
                    return v.encode('utf-8', 'ignore').decode('utf-8').strip()
                except Exception:
                    return str(v).strip()
            if isinstance(v, dict):
                return RegistryParser.sanitize_registry_data(v)
            if isinstance(v, list):
                return [clean_value(i) for i in v]
            return v

        return {k: clean_value(v) for k, v in data.items()}

    @staticmethod
    def truncate_massive_document(text: str, max_chars: int = 50000) -> str:
        """
        Truncates massive documents to prevent token overflow while preserving start and end.
        """
        if len(text) <= max_chars:
            return text
        
        half = max_chars // 2
        return text[:half] + "\n... [TRUNCATED] ...\n" + text[-half:]
