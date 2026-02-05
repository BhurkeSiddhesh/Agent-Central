import pytest
import asyncio
from unittest.mock import MagicMock, patch
import sys

# Mock azure.cognitiveservices.speech before importing azure_transcriber
# We need to mock the parent modules too because 'azure' is a namespace package
# and might be confusing import system if not consistent.

mock_speech = MagicMock()
mock_cognitiveservices = MagicMock()
mock_azure = MagicMock()

# We set them in sys.modules so imports find them
sys.modules["azure"] = mock_azure
sys.modules["azure.cognitiveservices"] = mock_cognitiveservices
sys.modules["azure.cognitiveservices.speech"] = mock_speech
sys.modules["azure.cognitiveservices.speech.audio"] = mock_speech.audio

# Link them together so attribute access works
mock_azure.cognitiveservices = mock_cognitiveservices
mock_cognitiveservices.speech = mock_speech

# Need to make sure we import the module after mocking
from ..transcribers.azure_transcriber import AzureTranscriber
from ..interfaces import Transcription

@pytest.mark.asyncio
async def test_azure_transcriber_initialization():
    config = {
        "azureSpeechKey": "test_key",
        "azureServiceRegion": "test_region",
        "language": "fr-FR"
    }

    transcriber = AzureTranscriber(config)

    assert transcriber.speech_key == "test_key"
    assert transcriber.service_region == "test_region"
    assert transcriber.language == "fr-FR"

    mock_speech.SpeechConfig.assert_called_with(subscription="test_key", region="test_region")

@pytest.mark.asyncio
async def test_transcribe_stream():
    config = {
        "azureSpeechKey": "test_key",
        "azureServiceRegion": "test_region"
    }
    transcriber = AzureTranscriber(config)

    # Mock Stream
    async def mock_audio_stream():
        yield b"chunk1"
        yield b"chunk2"

    # Mock Recognizer
    mock_recognizer = mock_speech.SpeechRecognizer.return_value

    # Setup connection mocking
    captured_callbacks = {}

    def side_effect_connect(event_name):
        def connect(callback):
            captured_callbacks[event_name] = callback
        return connect

    mock_recognizer.recognizing.connect.side_effect = side_effect_connect("recognizing")
    mock_recognizer.recognized.connect.side_effect = side_effect_connect("recognized")
    mock_recognizer.canceled.connect.side_effect = side_effect_connect("canceled")
    mock_recognizer.session_stopped.connect.side_effect = side_effect_connect("session_stopped")

    # Helper to collect results
    async def collect_transcriptions(generator):
        results = []
        async for item in generator:
            results.append(item)
        return results

    # Run transcribe_stream in a task
    task = asyncio.create_task(
        collect_transcriptions(transcriber.transcribe_stream(mock_audio_stream()))
    )

    # Give it a moment to start and register callbacks
    # Using a small sleep loop to wait until callbacks are registered
    for _ in range(10):
        if len(captured_callbacks) == 4:
            break
        await asyncio.sleep(0.01)

    assert "recognizing" in captured_callbacks
    assert "recognized" in captured_callbacks

    # Simulate events
    loop = asyncio.get_running_loop()

    # recognizing
    evt = MagicMock()
    evt.result.text = "Hello"
    captured_callbacks["recognizing"](evt)

    # recognized
    evt_final = MagicMock()
    evt_final.result.text = "Hello world."
    captured_callbacks["recognized"](evt_final)

    # stop session
    captured_callbacks["session_stopped"](MagicMock())

    # Wait for task
    results = await task

    assert len(results) == 2
    assert results[0].message == "Hello"
    assert results[0].is_final == False
    assert results[0].is_interrupt == True
    assert results[1].message == "Hello world."
    assert results[1].is_final == True
