"""Local TTS implementation using Piper"""
import asyncio
import subprocess
import tempfile
import wave
import os
from typing import AsyncIterable, List, Optional
from dataclasses import dataclass
from livekit import agents, rtc
from livekit.agents import tts
import numpy as np
import logging
from pathlib import Path
from .piper_options import PiperOptions

logger = logging.getLogger(__name__)


class LocalPiperTTS(tts.TTS):
    def __init__(
        self,
        *,
        model_path: str = None,
        config_path: str = None,
        speaker_id: int = 0,
        length_scale: float = 1.0,
        noise_scale: float = 0.667,
        noise_w: float = 0.8,
        piper_executable: str = "piper",
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
        self._options = PiperOptions(
            model_path=model_path,
            config_path=config_path,
            speaker_id=speaker_id,
            length_scale=length_scale,
            noise_scale=noise_scale,
            noise_w=noise_w,
            output_sample_rate=sample_rate,
        )
        self._piper_executable = piper_executable
        self._validate_setup()
    
    def _resample_audio(self, audio_data: bytes, from_rate: int, to_rate: int) -> bytes:
        """Resample audio data to a different sample rate"""
        import numpy as np
        import scipy.signal
        
        # Convert bytes to numpy array
        audio_array = np.frombuffer(audio_data, dtype=np.int16)
        
        # Calculate resampling ratio
        ratio = to_rate / from_rate
        
        # Resample
        resampled_length = int(len(audio_array) * ratio)
        resampled = scipy.signal.resample(audio_array, resampled_length)
        
        # Convert back to int16
        resampled = np.clip(resampled, -32768, 32767).astype(np.int16)
        
        return resampled.tobytes()

    def _validate_setup(self):
        """Validate Piper installation and model files"""
        # Check if piper is available
        try:
            # Try with devenv first
            result = subprocess.run(["devenv", "shell", "--", "piper", "--version"], capture_output=True)
            if result.returncode == 0:
                self._use_devenv = True
                logger.info("Piper executable found in devenv")
            else:
                # Try direct piper
                subprocess.run([self._piper_executable, "--version"], capture_output=True, check=True)
                self._use_devenv = False
                logger.info("Piper executable found")
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError(f"Piper not found. Please install Piper TTS.")

        # Check model files if provided
        if self._options.model_path and not Path(self._options.model_path).exists():
            raise RuntimeError(f"Model file not found: {self._options.model_path}")
        if self._options.config_path and not Path(self._options.config_path).exists():
            raise RuntimeError(f"Config file not found: {self._options.config_path}")

    async def synthesize(
        self,
        text: str,
        *,
        voice: Optional[str] = None,
    ) -> tts.SynthesizedAudio:
        """Synthesize speech from text"""
        logger.info(f"[Piper] Synthesizing text: '{text}'")
        
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
        """Run Piper synthesis synchronously"""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            tmp_path = tmp_file.name

        try:
            # Build Piper command
            if hasattr(self, '_use_devenv') and self._use_devenv:
                cmd = ["devenv", "shell", "--", "piper"]
            else:
                cmd = [self._piper_executable]
            
            if self._options.model_path:
                cmd.extend(["--model", self._options.model_path])
            if self._options.config_path:
                cmd.extend(["--config", self._options.config_path])
            
            cmd.extend([
                "--speaker", str(self._options.speaker_id),
                "--length-scale", str(self._options.length_scale),
                "--noise-scale", str(self._options.noise_scale),
                "--noise-w", str(self._options.noise_w),
                "--output-file", tmp_path,
            ])

            # Run Piper
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            stdout, stderr = process.communicate(input=text)

            if process.returncode != 0:
                raise RuntimeError(f"Piper synthesis failed: {stderr}")

            # Read the generated audio and get actual sample rate
            with wave.open(tmp_path, "rb") as wav_file:
                actual_sample_rate = wav_file.getframerate()
                actual_channels = wav_file.getnchannels()
                frames = wav_file.readframes(wav_file.getnframes())
                
                # Log the actual format
                logger.info(f"Piper output: {actual_sample_rate}Hz, {actual_channels} channels, {wav_file.getnframes()} frames")
                
                # If sample rate doesn't match expected, resample
                if actual_sample_rate != self._sample_rate:
                    logger.info(f"Resampling from {actual_sample_rate}Hz to {self._sample_rate}Hz")
                    frames = self._resample_audio(frames, actual_sample_rate, self._sample_rate)
                
            return frames

        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def stream(self, *, voice: Optional[str] = None) -> "PiperTTSStream":
        """Create a streaming interface"""
        from .piper_tts_stream import PiperTTSStream
        return PiperTTSStream(tts=self, voice=voice)
