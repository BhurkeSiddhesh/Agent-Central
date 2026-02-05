import sys
import os
import unittest
from unittest.mock import MagicMock
import logging

# Add the templates directory to path so we can import modules
# The tests are in agency-hq/skills/voice-ai-engine-development/tests
# The templates are in agency-hq/skills/voice-ai-engine-development/templates
# So we go up one level and then into templates
templates_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'templates')
sys.path.append(templates_path)

# Mock boto3 and botocore before importing the synthesizer
sys.modules["boto3"] = MagicMock()
sys.modules["botocore"] = MagicMock()
sys.modules["botocore.exceptions"] = MagicMock()

try:
    from multi_provider_factory_template import VoiceComponentFactory
    from synthesizers.polly import PollySynthesizer
except ImportError as e:
    print(f"Import failed: {e}")
    sys.exit(1)

class TestPollySynthesizer(unittest.TestCase):
    def test_factory_creates_polly(self):
        factory = VoiceComponentFactory()
        config = {
            "voiceProvider": "polly",
            "pollyAccessKey": "test_key",
            "pollySecretKey": "test_secret",
            "pollyRegion": "us-west-2",
            "pollyVoiceId": "Matthew"
        }

        synthesizer = factory.create_synthesizer(config)

        self.assertIsInstance(synthesizer, PollySynthesizer)
        self.assertEqual(synthesizer.voice_id, "Matthew")

        # Check if boto3 client was initialized with correct params
        import boto3
        boto3.client.assert_called_with(
            'polly',
            aws_access_key_id="test_key",
            aws_secret_access_key="test_secret",
            region_name="us-west-2"
        )
        print("✅ Factory created Polly synthesizer successfully")

    def test_factory_default_params(self):
        factory = VoiceComponentFactory()
        config = {
            "voiceProvider": "polly"
        }

        synthesizer = factory.create_synthesizer(config)
        self.assertEqual(synthesizer.voice_id, "Joanna")
        self.assertEqual(synthesizer.engine, "neural")
        print("✅ Factory used defaults successfully")

if __name__ == "__main__":
    unittest.main()
