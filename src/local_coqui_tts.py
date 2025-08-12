# Alternative Coqui TTS implementation
class LocalCoquiTTS(tts.TTS):
    """Local TTS using Coqui TTS (XTTS v2)"""
    
    def __init__(
        self,
        *,
        model_name: str = "tts_models/en/ljspeech/tacotron2-DDC",
        speaker_wav: Optional[str] = None,
        language: str = "en",
        sample_rate: int = 22050,
        num_channels: int = 1,
    ):
        super().__init__(
            capabilities=tts.TTSCapabilities(
                streaming=False,
            ),
            sample_rate=sample_rate,
            num_channels=num_channels,
        )
        self._model_name = model_name
        self._speaker_wav = speaker_wav
        self._language = language
        self._tts = None
        self._initialize_model()

    def _initialize_model(self):
        """Initialize Coqui TTS model"""
        try:
            from TTS.api import TTS
            logger.info(f"Loading Coqui TTS model: {self._model_name}")
            self._tts = TTS(self._model_name)
            logger.info("Coqui TTS model loaded successfully")
        except ImportError:
            raise RuntimeError("Coqui TTS not installed. Run: pip install TTS")

    async def synthesize(
        self,
        text: str,
        *,
        voice: Optional[str] = None,
    ) -> tts.SynthesizedAudio:
        """Synthesize speech from text"""
        logger.info(f"Synthesizing text with Coqui: '{text}'")
        
        # Run synthesis in thread pool
        loop = asyncio.get_event_loop()
        audio_data = await loop.run_in_executor(None, self._synthesize_sync, text)

        # Create an AudioFrame from the raw audio data
        samples_per_channel = len(audio_data) // (2 * self._num_channels)  # 16-bit = 2 bytes per sample
        frame = rtc.AudioFrame.create(
            sample_rate=self._sample_rate,
            num_channels=self._num_channels,
            samples_per_channel=samples_per_channel,
        )
        
        # Copy audio data to frame using numpy to handle the memoryview properly
        import numpy as np
        frame_array = np.frombuffer(frame.data, dtype=np.int16)
        audio_array = np.frombuffer(audio_data, dtype=np.int16)
        frame_array[:] = audio_array
        
        return tts.SynthesizedAudio(
            frame=frame,
            request_id="",  # Required but not used for non-streaming
            is_final=True,
        )

    def _synthesize_sync(self, text: str) -> bytes:
        """Run Coqui synthesis synchronously"""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            tmp_path = tmp_file.name

        try:
            # Synthesize to file
            if self._speaker_wav:
                self._tts.tts_to_file(
                    text=text,
                    speaker_wav=self._speaker_wav,
                    language=self._language,
                    file_path=tmp_path,
                )
            else:
                self._tts.tts_to_file(
                    text=text,
                    file_path=tmp_path,
                )

            # Read the generated audio
            with wave.open(tmp_path, "rb") as wav_file:
                # Get just the PCM data without WAV headers
                frames = wav_file.readframes(wav_file.getnframes())
                
                # Log for debugging
                logger.debug(f"Generated audio: {wav_file.getnframes()} frames, {len(frames)} bytes")
                
            return frames

        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def stream(self, *, voice: Optional[str] = None) -> tts.SynthesizeStream:
        """Create a streaming interface"""
        # Similar implementation to PiperTTSStream
        raise NotImplementedError("Streaming not implemented for Coqui TTS")