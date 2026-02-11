"""
Amazon Polly Synthesizer Implementation
"""

import asyncio
import logging
from typing import Any, Dict, Optional

try:
    import boto3
except ImportError:
    boto3 = None

try:
    from ..interfaces import TTSProvider
except ImportError:
    # Fallback for when run as top-level package member
    try:
        from interfaces import TTSProvider
    except ImportError:
        import os
        import sys

        # Last resort: add parent directory to path
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
        from interfaces import TTSProvider

logger = logging.getLogger(__name__)


class PollySynthesizer(TTSProvider):
    """
    Amazon Polly TTS Synthesizer
    """

    def __init__(
        self,
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
        region_name: str = "us-east-1",
        voice_id: str = "Joanna",
        engine: str = "standard",
        output_format: str = "mp3",
    ):
        """
        Initialize Polly synthesizer

        Args:
            access_key_id: AWS access key ID
            secret_access_key: AWS secret access key
            region_name: AWS region name
            voice_id: Polly voice ID (default: Joanna)
            engine: Polly engine (standard or neural)
            output_format: Output format (mp3, pcm, etc.)
        """
        if boto3 is None:
            raise ImportError(
                "boto3 is not installed. Please install it with `pip install boto3`."
            )

        self.voice_id = voice_id
        self.engine = engine
        self.output_format = output_format

        try:
            # boto3 client creation might do IO or validation, but usually fast.
            # Credentials can be None to use default chain.
            self.client = boto3.client(
                "polly",
                region_name=region_name,
                aws_access_key_id=access_key_id,
                aws_secret_access_key=secret_access_key,
            )
        except Exception as e:
            logger.error(f"Failed to initialize Polly client: {e}")
            raise

    async def synthesize_speech(self, text: str) -> bytes:
        """
        Synthesize speech from text using Amazon Polly.

        Args:
            text: The text to synthesize

        Returns:
            bytes: The audio data
        """
        try:
            # Run blocking boto3 call in a separate thread
            response = await asyncio.to_thread(self._synthesize_sync, text)

            if "AudioStream" in response:
                # Read the stream (also blocking IO) in a thread
                # Note: response['AudioStream'] is a botocore.response.StreamingBody
                audio_data = await asyncio.to_thread(response["AudioStream"].read)
                return audio_data
            else:
                raise RuntimeError("No AudioStream in Polly response")

        except Exception as e:
            logger.error(f"Error synthesizing speech with Polly: {e}")
            raise

    def _synthesize_sync(self, text: str):
        """Synchronous wrapper for synthesize_speech call"""
        return self.client.synthesize_speech(
            Text=text,
            OutputFormat=self.output_format,
            VoiceId=self.voice_id,
            Engine=self.engine,
        )
