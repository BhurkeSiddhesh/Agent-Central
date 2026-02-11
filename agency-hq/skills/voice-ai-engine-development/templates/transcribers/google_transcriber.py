"""
Google Cloud Speech-to-Text Transcriber Implementation
"""

import logging
from typing import AsyncGenerator, Dict, Any, Optional

from ..interfaces import TranscriberProvider

logger = logging.getLogger(__name__)

try:
    from google.cloud import speech
    from google.api_core import exceptions
except ImportError:
    logger.warning("Google Cloud Speech library not found. Please install `google-cloud-speech`.")
    speech = None
    exceptions = None

class GoogleTranscriber(TranscriberProvider):
    """
    Transcriber using Google Cloud Speech-to-Text API.

    Requires `google-cloud-speech` package.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Google Transcriber

        Args:
            config: Configuration dictionary containing:
                - googleCredentials: (Optional) JSON string of credentials
                - language: (Optional) Language code (default: en-US)
                - sampleRate: (Optional) Audio sample rate (default: 16000)
                - encoding: (Optional) Audio encoding (default: LINEAR16)
        """
        if speech is None:
            raise ImportError("Google Cloud Speech library not found. Please install `google-cloud-speech`.")

        self.config = config
        self.language_code = config.get("language", "en-US")
        self.sample_rate = config.get("sampleRate", 16000)

        # Allow configuring encoding, default to LINEAR16
        encoding_str = config.get("encoding", "LINEAR16").upper()
        self.encoding = getattr(speech.RecognitionConfig.AudioEncoding, encoding_str, speech.RecognitionConfig.AudioEncoding.LINEAR16)

        # Initialize client
        # Note: In production, credentials should be handled via environment variables
        # (GOOGLE_APPLICATION_CREDENTIALS) or passed explicitly.
        self.client = speech.SpeechAsyncClient()

    async def transcribe_stream(self, audio_stream: AsyncGenerator[bytes, None]) -> AsyncGenerator[str, None]:
        """
        Transcribe streaming audio

        Args:
            audio_stream: Async generator yielding audio chunks (bytes)

        Yields:
            Transcribed text (str) - Only final results
        """

        # 1. Configure request
        config = speech.RecognitionConfig(
            encoding=self.encoding,
            sample_rate_hertz=self.sample_rate,
            language_code=self.language_code,
            enable_automatic_punctuation=True,
        )

        streaming_config = speech.StreamingRecognitionConfig(
            config=config,
            interim_results=True  # We still request interim results for potential future use or better VAD
        )

        # 2. Create request generator
        async def request_generator():
            # Initial configuration request
            yield speech.StreamingRecognizeRequest(streaming_config=streaming_config)

            # Audio chunks
            async for chunk in audio_stream:
                if not chunk:
                    continue
                yield speech.StreamingRecognizeRequest(audio_content=chunk)

        # 3. Start streaming recognition
        requests = request_generator()

        try:
            # streaming_recognize returns an async generator of responses
            responses = await self.client.streaming_recognize(requests=requests)

            async for response in responses:
                if not response.results:
                    continue

                # We are interested in the first result
                result = response.results[0]
                if not result.alternatives:
                    continue

                # Only yield final results to avoid duplicating text in downstream consumers
                if result.is_final:
                    transcript = result.alternatives[0].transcript
                    if transcript:
                        yield transcript

        except exceptions.GoogleAPICallError as e:
            logger.error(f"Google Speech API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error in Google Transcriber: {e}")
            raise
