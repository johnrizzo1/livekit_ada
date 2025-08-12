"""Stream adapter for Whisper using VAD for segmentation"""
from typing import TYPE_CHECKING
from livekit import rtc
from livekit.agents import stt, APIConnectOptions
from livekit.agents.utils import AudioBuffer

if TYPE_CHECKING:
    from .local_whisper_stt import LocalWhisperSTT


class WhisperSTTStream(stt.SpeechStream):
    """Stream adapter for Whisper using VAD for segmentation"""
    
    def __init__(self, stt: "LocalWhisperSTT", language: str):
        super().__init__(stt=stt, conn_options=APIConnectOptions())
        self._stt = stt
        self._language = language
        self._audio_buffer = []
        self._sample_rate = 16000
    
    async def _run(self) -> None:
        """Required implementation for abstract method"""
        # This method is called by the framework to start the stream
        pass
        
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
        event = await self._stt.recognize(
            buffer=audio_buffer, language=self._language
        )
        
        # Clear buffer
        self._audio_buffer.clear()
        
        # Emit the event
        if event.alternatives:
            self._event_ch.send_nowait(event)
            
    async def aclose(self) -> None:
        """Close the stream"""
        await self.flush()
        await super().aclose()