from typing import Optional
from livekit.agents import tts
from .local_piper_tts import LocalPiperTTS


class PiperTTSStream(tts.SynthesizeStream):
    """Stream adapter for Piper TTS"""
    
    def __init__(self, tts: LocalPiperTTS, voice: Optional[str] = None):
        super().__init__()
        self._tts = tts
        self._voice = voice
        
    async def push_text(self, text: str) -> None:
        """Add text to be synthesized"""
        if not text.strip():
            return
            
        # Synthesize the text
        result = await self._tts.synthesize(text, voice=self._voice)
        
        # Emit the synthesized audio through the proper channel
        self._event_ch.send_nowait(result)
            
    async def flush(self) -> None:
        """Flush any pending synthesis"""
        pass
        
    async def aclose(self) -> None:
        """Close the stream"""
        await super().aclose()

