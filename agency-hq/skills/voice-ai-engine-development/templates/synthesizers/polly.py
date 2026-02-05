import logging
from typing import Dict, Any, AsyncGenerator, Optional
import asyncio

try:
    import boto3
    from botocore.exceptions import BotoCoreError, ClientError
except ImportError:
    boto3 = None

# Try relative import first (when used as package), fallback to direct import (for testing)
try:
    from ..interfaces import TTSProvider
except (ImportError, ValueError):
    # This might happen if we are running this file directly or in a way that doesn't support relative imports
    # In a real scenario, we should ensure the path is correct.
    # For now, we assume interfaces is in the parent directory.
    import sys
    import os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from interfaces import TTSProvider

logger = logging.getLogger(__name__)

class PollySynthesizer(TTSProvider):
    """
    Amazon Polly TTS Synthesizer
    """

    def __init__(self,
                 aws_access_key_id: Optional[str] = None,
                 aws_secret_access_key: Optional[str] = None,
                 region_name: str = "us-east-1",
                 voice_id: str = "Joanna",
                 engine: str = "neural",
                 sample_rate: str = "16000"):
        """
        Initialize Polly synthesizer

        Args:
            aws_access_key_id: AWS access key
            aws_secret_access_key: AWS secret key
            region_name: AWS region
            voice_id: Voice ID (e.g., "Joanna", "Matthew")
            engine: Engine type ("standard", "neural", "long-form")
            sample_rate: Sample rate in Hz (default: 16000)
        """
        if boto3 is None:
            raise ImportError("boto3 is required for PollySynthesizer. Please install it with 'pip install boto3'")

        self.voice_id = voice_id
        self.engine = engine
        self.sample_rate = sample_rate

        try:
            self.client = boto3.client(
                'polly',
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                region_name=region_name
            )
        except Exception as e:
            logger.error(f"Failed to initialize Polly client: {e}")
            raise

    async def synthesize_speech(self, text: str) -> AsyncGenerator[bytes, None]:
        """
        Synthesize speech from text using Amazon Polly

        Args:
            text: Text to synthesize

        Yields:
            Audio chunks (PCM)
        """
        try:
            # Polly create_speech logic
            # Note: boto3 is synchronous, so we run it in a thread executor to avoid blocking the loop
            loop = asyncio.get_running_loop()

            def _call_polly():
                return self.client.synthesize_speech(
                    Text=text,
                    OutputFormat='pcm',
                    VoiceId=self.voice_id,
                    Engine=self.engine,
                    SampleRate=self.sample_rate
                )

            response = await loop.run_in_executor(None, _call_polly)

            # The 'AudioStream' is a botocore.response.StreamingBody
            if 'AudioStream' in response:
                stream = response['AudioStream']

                # StreamingBody.read() is synchronous, so we should also run reading in executor
                # or read in small chunks.
                # However, for simplicity and since we want to yield, we can read chunks.

                chunk_size = 1024 * 4  # 4KB chunks

                while True:
                    def _read_chunk():
                        return stream.read(chunk_size)

                    chunk = await loop.run_in_executor(None, _read_chunk)
                    if not chunk:
                        break
                    yield chunk
            else:
                logger.error("No AudioStream in Polly response")

        except (BotoCoreError, ClientError) as e:
            logger.error(f"Polly synthesis failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in Polly synthesis: {e}")
            raise
