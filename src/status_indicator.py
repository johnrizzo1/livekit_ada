import time


class StatusIndicator:
    """Manages status display"""
    def __init__(self):
        self.current_status = ""
        self.audio_level = 0
        self.is_recording = False
        self.is_transcribing = False
        self.is_thinking = False
        self.is_speaking = False
        self.is_dictating = False
        self.last_update = time.time()
        
    def update_audio_level(self, rms):
        """Update audio level indicator"""
        self.audio_level = rms
        self._print_status()
        
    def set_recording(self, recording):
        """Set recording status"""
        self.is_recording = recording
        self._print_status()
        
    def set_transcribing(self, transcribing):
        """Set transcribing status"""
        self.is_transcribing = transcribing
        self._print_status()
        
    def set_thinking(self, thinking):
        """Set LLM thinking status"""
        self.is_thinking = thinking
        self._print_status()
        
    def set_speaking(self, speaking):
        """Set TTS speaking status"""
        self.is_speaking = speaking
        self._print_status()
        
    def set_dictating(self, dictating):
        """Set dictation mode status"""
        self.is_dictating = dictating
        self._print_status()
        
    def _print_status(self):
        """Print current status line"""
        # Rate limit updates
        if time.time() - self.last_update < 0.1:
            return
        self.last_update = time.time()
        
        # Build status line
        meter_level = min(10, int(self.audio_level / 1000))
        meter = "█" * meter_level + "░" * (10 - meter_level)
        
        # Audio level indicator
        if self.audio_level < 200:
            audio_status = "🔇"
        elif self.audio_level < 1000:
            audio_status = "🔉"
        else:
            audio_status = "🔊"
            
        # Pipeline status
        pipeline_parts = []
        if self.is_dictating:
            pipeline_parts.append("📝 DICTATING")
        if self.is_recording:
            pipeline_parts.append("🔴 RECORDING")
        if self.is_transcribing:
            pipeline_parts.append("🎙️ TRANSCRIBING")
        if self.is_thinking:
            pipeline_parts.append("🤔 THINKING")
        if self.is_speaking:
            pipeline_parts.append("📢 SPEAKING")
            
        if not pipeline_parts:
            pipeline_parts.append("⚪ LISTENING")
            
        pipeline_status = " → ".join(pipeline_parts)
        
        # Print status line
        status_line = f"\r{audio_status} [{meter}] {self.audio_level:4d} | {pipeline_status}"
        print(status_line + " " * 20, end="", flush=True)

