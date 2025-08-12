from typing import Callable
from datetime import datetime


class ConversationManager:
    """Manages conversation history and display"""
    def __init__(self, max_messages: int = 100):
        self.messages = []
        self.max_messages = max_messages
        self.update_callback = None
        
    def set_update_callback(self, callback: Callable):
        """Set callback for UI updates"""
        self.update_callback = callback
        
    def add_user_message(self, text: str):
        """Add user message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.messages.append({
            "type": "user",
            "text": text,
            "timestamp": timestamp
        })
        self._trim_messages()
        if self.update_callback:
            self.update_callback()
            
    def add_agent_message(self, text: str):
        """Add agent message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.messages.append({
            "type": "agent", 
            "text": text,
            "timestamp": timestamp
        })
        self._trim_messages()
        if self.update_callback:
            self.update_callback()
            
    def add_system_message(self, text: str):
        """Add system message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.messages.append({
            "type": "system",
            "text": text, 
            "timestamp": timestamp
        })
        self._trim_messages()
        if self.update_callback:
            self.update_callback()
            
    def _trim_messages(self):
        """Keep only recent messages"""
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]
            
    def get_recent_messages(self, count: int = 20) -> list:
        """Get recent messages for display"""
        return self.messages[-count:] if self.messages else []

