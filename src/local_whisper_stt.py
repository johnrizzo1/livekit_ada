"""Local STT implementation using faster-whisper"""
import asyncio
import numpy as np
from typing import Optional
from faster_whisper import WhisperModel
from livekit import agents
from livekit.agents import stt, APIConnectOptions
from livekit.agents.utils import AudioBuffer
import logging

from .whisper_options import WhisperOptions

logger = logging.getLogger(__name__)


class LocalWhisperSTT(stt.STT):
    """Local Speech-to-Text implementation using faster-whisper.
    
    This class provides speech recognition capabilities using a locally-running
    Whisper model via the faster-whisper library. It supports various model sizes,
    devices, and compute types for flexible deployment options. The implementation
    provides non-streaming recognition with configurable VAD filtering.
    
    Args:
        model_size: Whisper model size ("tiny", "base", "small", "medium", "large")
        device: Device to run inference on ("auto", "cpu", "cuda")
        compute_type: Compute precision ("int8", "float16", "float32")
        language: Target language for transcription (default: "en")
        initial_prompt: Optional prompt to guide transcription
        vad_filter: Whether to apply voice activity detection filtering
    """
    
    def __init__(
        self,
        *,
        model_size: str = "base",
        device: str = "auto",
        compute_type: str = "int8",
        language: str = "en",
        initial_prompt: Optional[str] = None,
        vad_filter: bool = True,
    ):
        super().__init__(
            capabilities=stt.STTCapabilities(
                streaming=False,
                interim_results=False,
            )
        )
        self._options = WhisperOptions(
            model_size=model_size,
            device=device,
            compute_type=compute_type,
            language=language,
            initial_prompt=initial_prompt,
            vad_filter=vad_filter,
        )
        self._model = None
        self._initialize_model()

    def _initialize_model(self):
        """Initialize the Whisper model"""
        logger.info(f"Loading Whisper model: {self._options.model_size}")
        self._model = WhisperModel(
            self._options.model_size,
            device=self._options.device,
            compute_type=self._options.compute_type,
        )
        logger.info("Whisper model loaded successfully")

    async def _recognize_impl(
        self,
        buffer: AudioBuffer,
        *,
        language: Optional[str] = None,
        conn_options: APIConnectOptions,
    ) -> stt.SpeechEvent:
        """Recognize speech from audio buffer"""

        # Convert audio to numpy array  
        if isinstance(buffer, list):
            # Handle case where buffer is a list of AudioFrames
            raise ValueError("Buffer should be AudioBuffer, not list of frames")
        elif hasattr(buffer, 'data'):
            audio_data = np.frombuffer(buffer.data, dtype=np.int16).astype(np.float32)
        else:
            raise ValueError("Invalid buffer format - expected AudioBuffer with data attribute")
        audio_data = audio_data / 32768.0  # Normalize to [-1, 1]

        # Run inference in thread pool
        loop = asyncio.get_event_loop()
        segments, info = await loop.run_in_executor(
            None,
            self._transcribe,
            audio_data,
            language or self._options.language,
        )

        # Combine all segments
        text = " ".join([segment.text.strip() for segment in segments])
        
        if not text:
            return stt.SpeechEvent(
                type=stt.SpeechEventType.END_OF_SPEECH,
                alternatives=[],
            )

        return stt.SpeechEvent(
            type=stt.SpeechEventType.FINAL_TRANSCRIPT,
            alternatives=[
                stt.SpeechData(
                    text=text,
                    language=info.language,
                    confidence=1.0,
                )
            ],
        )

    def _transcribe(self, audio_data: np.ndarray, language: str):
        """Run Whisper transcription"""
        if self._model is None:
            raise RuntimeError("Whisper model not initialized")
        segments, info = self._model.transcribe(
            audio_data,
            beam_size=5,
            language=language,
            initial_prompt=self._options.initial_prompt,
            vad_filter=self._options.vad_filter,
        )
        return list(segments), info

    def stream(
        self,
        *,
        language: Optional[str] = None,
    ) -> "WhisperSTTStream":
        """Create a streaming interface (uses VAD for segmentation)"""
        from .whisper_stt_stream import WhisperSTTStream
        return WhisperSTTStream(
            stt=self,
            language=language or self._options.language,
        )