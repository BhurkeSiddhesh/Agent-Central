import asyncio
import logging
from typing import AsyncGenerator, Dict, Any, Optional

try:
    import azure.cognitiveservices.speech as speechsdk
except ImportError as e:
    print(f"DEBUG: ImportError during azure import: {e}")
    speechsdk = None

from ..interfaces import TranscriberProvider, Transcription

logger = logging.getLogger(__name__)

class AzureTranscriber(TranscriberProvider):
    """
    Azure Speech Service implementation of TranscriberProvider.
    Requires 'azure-cognitiveservices-speech' package.
    """

    def __init__(self, config: Dict[str, Any]):
        if speechsdk is None:
            raise ImportError(
                "Azure Speech SDK not installed. "
                "Run `pip install azure-cognitiveservices-speech`"
            )

        self.speech_key = config.get("azureSpeechKey")
        self.service_region = config.get("azureServiceRegion")
        self.language = config.get("language", "en-US")

        if not self.speech_key or not self.service_region:
            raise ValueError(
                "Azure configuration error: 'azureSpeechKey' and 'azureServiceRegion' are required."
            )

        self.speech_config = speechsdk.SpeechConfig(
            subscription=self.speech_key,
            region=self.service_region
        )
        self.speech_config.speech_recognition_language = self.language

        # Optional: Set output format to detailed if needed, but simple is usually enough
        # self.speech_config.output_format = speechsdk.OutputFormat.Detailed

    async def transcribe_stream(self, audio_stream: AsyncGenerator[bytes, None]) -> AsyncGenerator[Transcription, None]:
        """
        Transcribe audio from an async generator stream using Azure Speech SDK.
        """
        loop = asyncio.get_running_loop()
        queue = asyncio.Queue()

        # Audio stream setup - PushAudioInputStream allows us to write data to it
        push_stream = speechsdk.audio.PushAudioInputStream()
        audio_config = speechsdk.audio.AudioConfig(stream=push_stream)

        # Recognizer setup
        recognizer = speechsdk.SpeechRecognizer(
            speech_config=self.speech_config,
            audio_config=audio_config
        )

        # Event handlers
        def recognizing_cb(evt):
            """Callback for intermediate results"""
            if evt.result.text:
                transcription = Transcription(
                    message=evt.result.text,
                    is_final=False,
                    is_interrupt=True
                )
                loop.call_soon_threadsafe(queue.put_nowait, transcription)

        def recognized_cb(evt):
            """Callback for final results"""
            if evt.result.text:
                transcription = Transcription(
                    message=evt.result.text,
                    is_final=True,
                    confidence=1.0 # Simplified
                )
                loop.call_soon_threadsafe(queue.put_nowait, transcription)

        def canceled_cb(evt):
            """Callback for cancellation/error"""
            if evt.reason == speechsdk.CancellationReason.Error:
                 logger.error(f"Azure Speech Error: {evt.error_details}")
            elif evt.reason == speechsdk.CancellationReason.EndOfStream:
                 logger.info("Azure Speech: End of stream")

            # Signal end of stream
            loop.call_soon_threadsafe(queue.put_nowait, None)

        def session_stopped_cb(evt):
            """Callback for session stop"""
            loop.call_soon_threadsafe(queue.put_nowait, None)

        # Connect events
        recognizer.recognizing.connect(recognizing_cb)
        recognizer.recognized.connect(recognized_cb)
        recognizer.canceled.connect(canceled_cb)
        recognizer.session_stopped.connect(session_stopped_cb)

        # Start recognition
        # start_continuous_recognition_async is generic, we can await it or use non-async
        # The python SDK has start_continuous_recognition() which returns immediately (mostly)
        recognizer.start_continuous_recognition()
        logger.info("🎤 [Azure] Started continuous recognition")

        # Background task to push audio from the input stream to Azure
        async def push_audio():
            try:
                async for chunk in audio_stream:
                    push_stream.write(chunk)
            except Exception as e:
                logger.error(f"Error pushing audio to Azure: {e}")
            finally:
                push_stream.close()

        push_task = asyncio.create_task(push_audio())

        try:
            while True:
                item = await queue.get()
                if item is None:
                    break
                yield item
        finally:
            # Cleanup
            recognizer.stop_continuous_recognition()
            push_task.cancel()
            try:
                await push_task
            except asyncio.CancelledError:
                pass
