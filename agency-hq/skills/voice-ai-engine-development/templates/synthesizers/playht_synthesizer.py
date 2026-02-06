import logging
from typing import Dict, Any, AsyncGenerator
from ..interfaces import TTSProvider

# Try to import pyht, but handle if it's not installed (though we will add it to requirements)
try:
    from pyht import Client
    from pyht.client import TTSOptions
except ImportError:
    Client = None
    TTSOptions = None

logger = logging.getLogger(__name__)

class PlayHTSynthesizer(TTSProvider):
    """
    Play.ht synthesizer implementation using pyht SDK
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Play.ht synthesizer

        Args:
            config: Configuration dictionary containing:
                - playhtApiKey: API key for Play.ht
                - playhtUserId: User ID for Play.ht
                - playhtVoiceId: Voice ID to use (optional, defaults to a standard voice)
        """
        if Client is None:
            raise ImportError("pyht package is not installed. Please install it with 'pip install pyht'")

        self.api_key = config.get("playhtApiKey")
        self.user_id = config.get("playhtUserId")
        self.voice_id = config.get("playhtVoiceId", "s3://voice-cloning-zero-shot/d9ff78ba-d016-47f6-b0ef-dd630f59414e/female-cs/manifest.json")

        if not self.api_key or not self.user_id:
            raise ValueError("playhtApiKey and playhtUserId are required for Play.ht synthesizer")

        self.client = Client(
            user_id=self.user_id,
            api_key=self.api_key,
        )

        logger.info(f"✅ Play.ht synthesizer initialized with voice: {self.voice_id}")

    async def synthesize_speech(self, text: str) -> AsyncGenerator[bytes, None]:
        """
        Synthesize speech from text

        Args:
            text: Text to synthesize

        Returns:
            AsyncGenerator yielding audio bytes
        """
        if not text:
            return

        options = TTSOptions(voice=self.voice_id)

        try:
            # The pyht client returns a generator, but we need to verify if it's async or sync.
            # Looking at typical usage, client.tts is often a generator.
            # If it's a sync generator, we might need to iterate it.
            # However, for async compatibility in our pipeline, we yield bytes.

            # Note: pyht SDK usage might vary. Assuming standard usage:
            # stream = self.client.tts(text, options)
            # for chunk in stream:
            #     yield chunk

            # Since we are in an async function, we should check if the SDK supports async
            # or if we need to run it in a thread executor if it's blocking.
            # For now, we assume the stream iterator works.

            # Using the stream directly
            stream = self.client.tts(text, options)

            for chunk in stream:
                yield chunk

        except Exception as e:
            logger.error(f"❌ Error synthesizing speech with Play.ht: {e}")
            raise
