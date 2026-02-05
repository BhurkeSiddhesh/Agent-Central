from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class Transcription:
    message: str
    is_final: bool = False
    confidence: float = 1.0
    is_interrupt: bool = False

class TranscriberProvider(ABC):
    """Abstract base class for transcriber providers"""

    @abstractmethod
    async def transcribe_stream(self, audio_stream: AsyncGenerator[bytes, None]) -> AsyncGenerator[Transcription, None]:
        """Transcribe streaming audio"""
        pass

class LLMProvider(ABC):
    """Abstract base class for LLM providers"""

    @abstractmethod
    async def generate_response(self, messages, stream=True):
        """Generate response from messages"""
        pass

class TTSProvider(ABC):
    """Abstract base class for TTS providers"""

    @abstractmethod
    async def synthesize_speech(self, text):
        """Synthesize speech from text"""
        pass
