import asyncio
import logging
from typing import Dict, Any, AsyncGenerator, Callable, Optional, List, Tuple
from dataclasses import dataclass
import azure.cognitiveservices.speech as speechsdk

logger = logging.getLogger(__name__)

@dataclass
class SynthesisResult:
    chunk_generator: AsyncGenerator[bytes, None]
    get_message_up_to: Callable[[float], str]

class PushAudioOutputStreamCallback(speechsdk.audio.PushAudioOutputStreamCallback):
    """Callback for receiving audio data from Azure Synthesizer"""

    def __init__(self, queue: asyncio.Queue, loop: asyncio.AbstractEventLoop):
        super().__init__()
        self._queue = queue
        self._loop = loop

    def write(self, data: bytes) -> int:
        """Called by SDK when new audio data is available"""
        if self._loop.is_closed():
            return 0
        self._loop.call_soon_threadsafe(self._queue.put_nowait, data)
        return len(data)

    def close(self):
        """Called by SDK when stream is closed"""
        if not self._loop.is_closed():
            self._loop.call_soon_threadsafe(self._queue.put_nowait, None)

class AzureSynthesizer:
    """Azure TTS Synthesizer Implementation"""

    def __init__(self, config: Dict[str, Any]):
        self.speech_key = config.get("azureSpeechKey")
        self.service_region = config.get("azureSpeechRegion")
        self.voice_name = config.get("azureVoiceName", "en-US-JennyNeural")

        if not self.speech_key or not self.service_region:
            raise ValueError("azureSpeechKey and azureSpeechRegion are required for Azure Synthesizer")

        self.speech_config = speechsdk.SpeechConfig(
            subscription=self.speech_key,
            region=self.service_region
        )
        self.speech_config.speech_synthesis_voice_name = self.voice_name

        # Use Raw 16kHz 16-bit Mono PCM (no WAV headers)
        self.speech_config.set_speech_synthesis_output_format(
            speechsdk.SpeechSynthesisOutputFormat.Raw16Khz16BitMonoPcm
        )

    async def synthesize_speech(self, text: str) -> SynthesisResult:
        """
        Synthesize speech from text

        Returns:
            SynthesisResult containing chunk generator and interrupt handler
        """
        queue = asyncio.Queue()
        loop = asyncio.get_running_loop()

        # Create callback and stream for receiving audio
        stream_callback = PushAudioOutputStreamCallback(queue, loop)
        push_stream = speechsdk.audio.PushAudioOutputStream(stream_callback)
        audio_config = speechsdk.audio.AudioConfig(stream=push_stream)

        # Create synthesizer
        synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=self.speech_config,
            audio_config=audio_config
        )

        # Track word boundaries for interrupts
        word_boundaries: List[Tuple[float, int]] = []

        def word_boundary_callback(evt: speechsdk.SessionEventArgs):
            # evt.audio_offset is in ticks (100ns)
            # 10,000,000 ticks = 1 second
            seconds = evt.audio_offset / 10_000_000.0
            # evt.text_offset is character index in original text
            word_boundaries.append((seconds, evt.text_offset))

        synthesizer.synthesis_word_boundary.connect(word_boundary_callback)

        # Start synthesis asynchronously
        # We don't await the result here because we want to stream chunks
        # The result_future keeps the operation alive
        result_future = synthesizer.speak_text_async(text)

        async def chunk_generator():
            try:
                while True:
                    chunk = await queue.get()
                    if chunk is None:
                        break
                    yield chunk
            finally:
                # Ensure we clean up if generator is cancelled
                _ = result_future
                _ = synthesizer

        def get_message_up_to(seconds: float) -> str:
            """Return the text spoken up to the given time (in seconds)"""
            if not word_boundaries:
                # Fallback: if no boundaries yet, estimate?
                # Or just return empty string until we get events.
                return ""

            # Find the last word boundary that occurred before 'seconds'
            last_boundary_idx = -1
            for i, (boundary_time, _) in enumerate(word_boundaries):
                if boundary_time > seconds:
                    break
                last_boundary_idx = i

            if last_boundary_idx != -1:
                # Get text offset of the word
                _, text_offset = word_boundaries[last_boundary_idx]

                # We need to find the end of this word.
                # Simple approximation: read until next space or end of string
                end_idx = text_offset
                while end_idx < len(text) and not text[end_idx].isspace():
                    end_idx += 1

                return text[:end_idx]

            return ""

        return SynthesisResult(
            chunk_generator=chunk_generator(),
            get_message_up_to=get_message_up_to
        )
