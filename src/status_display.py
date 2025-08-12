

import time


class StatusDisplay:
    """Manages client status display"""
    def __init__(self):
        self.mic_level = 0
        self.is_speaking = False
        self.agent_speaking = False
        self.agent_listening = False
        self.connection_status = "Connecting..."
        self.last_update = time.time()
        
    def update_mic_level(self, rms):
        """Update microphone level"""
        self.mic_level = rms
        self.is_speaking = rms > 1000
        self._print_status()
        
    def set_agent_speaking(self, speaking):
        """Set agent speaking status"""
        self.agent_speaking = speaking
        self._print_status()
        
    def set_connection_status(self, status):
        """Set connection status"""
        self.connection_status = status
        self._print_status()
        
    def _print_status(self):
        """Print status line"""
        # Rate limit
        if time.time() - self.last_update < 0.1:
            return
        self.last_update = time.time()
        
        # Build mic meter
        meter_level = min(10, int(self.mic_level / 1000))
        meter = "█" * meter_level + "░" * (10 - meter_level)
        
        # Mic status
        if self.mic_level < 300:
            mic_status = "🔇 Silent"
        elif self.mic_level < 1000:
            mic_status = "🔉 Noise"
        else:
            mic_status = "🔊 SPEAKING"
            
        # Agent status
        if self.agent_speaking:
            agent_status = "🤖 AGENT SPEAKING"
        else:
            agent_status = "👂 AGENT LISTENING"
            
        # Status line
        status_line = (f"\r{mic_status} [{meter}] {self.mic_level:4d} | "
                      f"{agent_status} | {self.connection_status}")
        print(status_line + " " * 20, end="", flush=True)

