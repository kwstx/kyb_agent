import unittest
from unittest.mock import MagicMock, patch
import json
import httpx
import pybreaker
from src.tools.base import BaseResilientTool
from src.tools.parsers import RegistryParser

class MockTool(BaseResilientTool):
    name: str = "mock_tool"
    description: str = "A tool for testing resilience"
    
    def _run(self, *args, **kwargs):
        pass

class TestDeterministicTools(unittest.TestCase):

    def setUp(self):
        self.tool = MockTool()
        # Reset the circuit breaker before each test to ensure deterministic behavior
        from src.tools.base import db_breaker
        db_breaker.close()

    def test_registry_down_retries(self):
        """Test that the tool retries on failure (Registry Down)."""
        mock_func = MagicMock(side_effect=Exception("Connection refused"))
        
        with self.assertRaises(Exception):
            self.tool._run_with_resilience(mock_func)
        
        # Should have tried 3 times (default in BaseResilientTool)
        self.assertEqual(mock_func.call_count, 3)

    def test_rate_limit_handling(self):
        """Test that the tool handles rate limits (429) and eventually fails."""
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 429
        mock_response.text = "Too Many Requests"
        
        # Simulate httpx raising for status
        def side_effect():
            raise httpx.HTTPStatusError("Rate limit", request=MagicMock(), response=mock_response)
        
        mock_func = MagicMock(side_effect=side_effect)
        
        with self.assertRaises(httpx.HTTPStatusError):
            self.tool._run_with_resilience(mock_func)
        
        self.assertEqual(mock_func.call_count, 3)

    def test_circuit_breaker_tripping(self):
        """Test that the circuit breaker trips after repeated failures."""
        from src.tools.base import db_breaker
        
        mock_func = MagicMock(side_effect=Exception("API Down"))
        
        # fail_max is 5 for db_breaker in base.py
        for _ in range(5):
            with self.assertRaises(Exception):
                self.tool._run_with_resilience(mock_func)
        
        # The 6th call should immediately raise CircuitBreakerError without calling mock_func
        with self.assertRaises(pybreaker.CircuitBreakerError):
            self.tool._run_with_resilience(mock_func)
            
        self.assertEqual(mock_func.call_count, 5)

    def test_parser_non_latin_characters(self):
        """Test parser robustness with non-Latin characters (Chinese, Arabic, Cyrillic)."""
        raw_data = {
            "name": "北京科技公司",
            "address": "شارع النصر",
            "note": "Победа"
        }
        sanitized = RegistryParser.sanitize_registry_data(raw_data)
        self.assertEqual(sanitized["name"], "北京科技公司")
        self.assertEqual(sanitized["address"], "شارع النصر")
        self.assertEqual(sanitized["note"], "Победа")

    def test_parser_empty_fields(self):
        """Test parser handling of empty or null fields."""
        raw_data = {
            "name": "Acme Corp",
            "registration_number": None,
            "offices": [],
            "metadata": {}
        }
        sanitized = RegistryParser.sanitize_registry_data(raw_data)
        self.assertEqual(sanitized["registration_number"], "")
        self.assertEqual(sanitized["offices"], [])
        self.assertEqual(sanitized["metadata"], {})

    def test_parser_malformed_json(self):
        """Test parser robustness with malformed JSON."""
        malformed_json = '{"name": "Acme Corp", "status": "active", }' # Note the trailing comma
        parsed = RegistryParser.parse_json(malformed_json)
        self.assertEqual(parsed["error"], "malformed_json")
        
        # Test recovery from markdown-wrapped JSON
        wrapped_json = '```json\n{"name": "Acme Corp"}\n```'
        parsed = RegistryParser.parse_json(wrapped_json)
        self.assertEqual(parsed["name"], "Acme Corp")

    def test_parser_massive_document(self):
        """Test truncation of massive documents."""
        massive_text = "A" * 100000
        truncated = RegistryParser.truncate_massive_document(massive_text, max_chars=1000)
        self.assertEqual(len(truncated), 1021) # 1000 + len("\n... [TRUNCATED] ...\n")
        self.assertIn("[TRUNCATED]", truncated)
        self.assertTrue(truncated.startswith("A" * 500))
        self.assertTrue(truncated.endswith("A" * 500))

    def test_html_parsing(self):
        """Test HTML to text conversion robustness."""
        html = """
        <html>
            <head><style>.css { color: red; }</style></head>
            <body>
                <h1>Company Name</h1>
                <p>Address: 123 Main St</p>
                <script>alert('malicious');</script>
            </body>
        </html>
        """
        text = RegistryParser.parse_html_to_text(html)
        self.assertIn("Company Name", text)
        self.assertIn("Address: 123 Main St", text)
        self.assertNotIn("script", text.lower())
        self.assertNotIn("style", text.lower())

if __name__ == "__main__":
    unittest.main()
