"""Local STT implementation using faster-whisper"""
import asyncio
import numpy as np
from typing import AsyncIterable, List, Optional
from typing import Union
from dataclasses import dataclass
from faster_whisper import WhisperModel
from livekit import agents, rtc
from livekit.agents import stt, APIConnectOptions
from livekit.agents.utils import AudioBuffer
import logging

logger = logging.getLogger(__name__)


@dataclass
class WhisperOptions:
    model_size: str = "base"
    device: str = "auto"
    compute_type: str = "int8"
    language: str = "en"
    initial_prompt: str = None
    vad_filter: bool = True
    vad_parameters: dict = None


class LocalWhisperSTT(stt.STT):
    def __init__(
        self,
        *,
        model_size: str = "base",
        device: str = "auto",
        compute_type: str = "int8",
        language: str = "en",
        initial_prompt: str = None,
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
        audio_data = np.frombuffer(buffer.data, dtype=np.int16).astype(np.float32)
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
        language: str = None,
    ) -> "WhisperSTTStream":
        """Create a streaming interface (uses VAD for segmentation)"""
        return WhisperSTTStream(
            stt=self,
            language=language or self._options.language,
        )


class WhisperSTTStream(stt.SpeechStream):
    """Stream adapter for Whisper using VAD for segmentation"""
    
    def __init__(self, stt: LocalWhisperSTT, language: str):
        super().__init__()
        self._stt = stt
        self._language = language
        self._audio_buffer = []
        self._sample_rate = 16000
        
    async def push_frame(self, frame: rtc.AudioFrame) -> None:
        """Add audio frame to buffer"""
        self._audio_buffer.append(frame)
        
    async def flush(self) -> None:
        """Process buffered audio"""
        if not self._audio_buffer:
            return
            
        # Combine audio frames
        combined_frame = rtc.combine_audio_frames(self._audio_buffer)
        
        # Create AudioBuffer from combined frame
        audio_buffer = AudioBuffer(
            data=combined_frame.data,
            sample_rate=combined_frame.sample_rate,
            num_channels=combined_frame.num_channels
        )
        
        # Recognize the buffered audio
        event = await self._stt.recognize(buffer=audio_buffer, language=self._language)
        
        # Clear buffer
        self._audio_buffer.clear()
        
        # Emit the event
        if event.alternatives:
            self._event_queue.put_nowait(event)
            
    async def aclose(self) -> None:
        """Close the stream"""
        await self.flush()
        await super().aclose()