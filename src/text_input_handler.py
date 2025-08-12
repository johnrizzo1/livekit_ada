import threading
import time
from typing import Optional
from rich.console import Console
from .conversation_manager import ConversationManager
from .voice_client import VoiceClient


class TextInputHandler:
    """Handles text input in a separate thread"""
    def __init__(self, console: Console, conversation: ConversationManager, 
                 voice_client: Optional[VoiceClient] = None):
        self.console = console
        self.conversation = conversation
        self.voice_client = voice_client
        self.running = True
        self.input_thread = None
        
    def start(self):
        """Start input handling thread"""
        self.input_thread = threading.Thread(target=self._input_loop, daemon=True)
        self.input_thread.start()
        
    def stop(self):
        """Stop input handling"""
        self.running = False
        
    def _input_loop(self):
        """Input handling loop"""
        while self.running:
            try:
                # Use a simple input with timeout simulation
                # In a real implementation, you'd want async input handling
                time.sleep(0.1)
            except KeyboardInterrupt:
                break
