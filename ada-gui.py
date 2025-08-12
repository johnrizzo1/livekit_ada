#!/usr/bin/env python3
"""
Ada GUI Client - Beautiful Terminal Interface
Enhanced voice and text client with Rich TUI interface
"""
import argparse
import sys
import asyncio
import logging
from pathlib import Path
from datetime import datetime
import threading
import time
import queue
from typing import Optional

# Ensure src is in path
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from rich.console import Console
    from rich.live import Live
    from rich.layout import Layout
    from rich.panel import Panel
    from rich.text import Text
    from rich.table import Table
    from rich.align import Align
    import rich.box
    
    RICH_AVAILABLE = True
except ImportError:
    print("❌ Rich library not found. Install with: pip install rich")
    print("   Falling back to basic client interface...")
    RICH_AVAILABLE = False

from src.client import VoiceClient, StatusDisplay


class EnhancedConversationManager:
    """Enhanced conversation manager with text input integration"""
    def __init__(self, max_messages: int = 100):
        self.messages = []
        self.max_messages = max_messages
        self.update_callback = None
        self.text_to_voice_callback = None
        
    def set_callbacks(self, update_callback, text_to_voice_callback=None):
        """Set UI update and text-to-voice callbacks"""
        self.update_callback = update_callback
        self.text_to_voice_callback = text_to_voice_callback
        
    def add_user_message(self, text: str, source: str = "text"):
        """Add user message with source tracking"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        icon = "⌨️" if source == "text" else "🎤"
        self.messages.append({
            "type": "user",
            "text": text,
            "timestamp": timestamp,
            "source": source,
            "icon": icon
        })
        self._trim_messages()
        if self.update_callback:
            self.update_callback()
        
        # If text input, send to agent via data channel
        if source == "text" and self.text_to_voice_callback:
            self.text_to_voice_callback(text)
            
    def add_agent_message(self, text: str):
        """Add agent message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.messages.append({
            "type": "agent", 
            "text": text,
            "timestamp": timestamp,
            "icon": "🤖"
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
            "timestamp": timestamp,
            "icon": "ℹ️"
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


class TextInputManager:
    """Manages text input in a separate thread"""
    def __init__(self, conversation_manager: EnhancedConversationManager):
        self.conversation = conversation_manager
        self.input_queue = queue.Queue()
        self.running = True
        self.input_thread = None
        
    def start(self):
        """Start the input thread"""
        self.input_thread = threading.Thread(
            target=self._input_loop, 
            daemon=True
        )
        self.input_thread.start()
        
    def stop(self):
        """Stop the input thread"""
        self.running = False
        
    def _input_loop(self):
        """Main input handling loop"""
        print("\n💬 Text input ready! Type your messages and press Enter.")
        print("   Voice input also active via microphone.")
        print("   Press Ctrl+C to exit.\n")
        
        while self.running:
            try:
                # Get user input
                user_input = input("💬 You: ").strip()
                
                if user_input:
                    # Add to conversation with text source
                    self.conversation.add_user_message(user_input, "text")
                    
            except (EOFError, KeyboardInterrupt):
                break
            except Exception as e:
                logger.error(f"Input error: {e}")
                time.sleep(0.1)


class EnhancedStatusDisplay(StatusDisplay):
    """Enhanced status display with conversation integration"""
    def __init__(self, conversation_manager: EnhancedConversationManager):
        super().__init__()
        self.conversation = conversation_manager
        self.last_status_line = ""
        
    def _print_status(self):
        """Enhanced status display with better formatting"""
        # Rate limit
        if time.time() - self.last_update < 0.2:
            return
        self.last_update = time.time()
        
        # Build status components
        meter_level = min(15, int(self.mic_level / 600))
        meter = "█" * meter_level + "░" * (15 - meter_level)
        
        # Mic status with color coding
        if self.mic_level < 200:
            mic_status = "🔇 Silent"
        elif self.mic_level < 800:
            mic_status = "🔉 Noise"
        else:
            mic_status = "🔊 SPEAKING"
        
        # Agent status
        if self.agent_speaking:
            agent_status = "🤖 Ada SPEAKING"
        else:
            agent_status = "👂 Ada Listening"
        
        # Connection status
        conn_display = self.connection_status
        
        # Build status line
        status_line = (
            f"\r📊 {mic_status} [{meter}] {self.mic_level:4d} | "
            f"{agent_status} | {conn_display}"
        )
        
        # Only update if changed to reduce flicker
        if status_line != self.last_status_line:
            print(f"{status_line:<80}", end="", flush=True)
            self.last_status_line = status_line


class SimpleAdaClient:
    """Simple Ada client without Rich dependencies"""
    def __init__(self):
        self.conversation = EnhancedConversationManager()
        self.status_display = EnhancedStatusDisplay(self.conversation)
        self.voice_client = None
        self.input_manager = None
        
    def setup_callbacks(self):
        """Setup conversation callbacks"""
        def on_voice_message(sender, message):
            if sender == "user":
                self.conversation.add_user_message(message, "voice")
            elif sender == "agent":
                self.conversation.add_agent_message(message)
                
        self.conversation.set_callbacks(
            update_callback=lambda: None,  # No GUI updates needed
        )
        
        # Setup voice client with conversation callback
        self.voice_client = VoiceClient(
            self.status_display, 
            on_voice_message
        )
        
    async def run(self, room_name: str = "ada-room"):
        """Run the simple client"""
        print("\n🎯 Ada Voice & Text Client")
        print("=" * 60)
        print(f"Room: {room_name}")
        print("=" * 60)
        
        # Setup callbacks
        self.setup_callbacks()
        
        # Start text input manager
        self.input_manager = TextInputManager(self.conversation)
        self.input_manager.start()
        
        # Add welcome message
        self.conversation.add_system_message(f"Connecting to room: {room_name}")
        
        try:
            # Connect voice client
            await self.voice_client.connect(room_name)
            self.conversation.add_system_message("✅ Voice connection established")
            self.conversation.add_system_message("💬 Text input ready - type and press Enter")
            
            # Main loop
            while True:
                await asyncio.sleep(0.1)
                
        except KeyboardInterrupt:
            print("\n\n👋 Shutting down...")
        finally:
            if self.input_manager:
                self.input_manager.stop()
            if self.voice_client:
                await self.voice_client.disconnect()


def setup_logging(log_level: str = "INFO", log_file: str = None):
    """Setup logging configuration"""
    if not log_file:
        log_file = f"logs/gui_client_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    # Create logs directory
    Path("logs").mkdir(exist_ok=True)
    
    # Configure logging to file only (no console output)
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
        ]
    )
    
    return log_file


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Ada GUI Client - Beautiful Voice & Text Interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # Connect to default room
  %(prog)s --room my-room     # Connect to specific room
  %(prog)s --debug           # Enable debug logging
  
Features:
  • Voice input via microphone
  • Text input via keyboard
  • Real-time status indicators
  • Conversation history
  • Rich terminal interface (when available)
        """
    )
    
    parser.add_argument(
        "--room",
        default="ada-room",
        help="LiveKit room name to join (default: ada-room)"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)"
    )
    
    parser.add_argument(
        "--log-file",
        help="Log file path (default: logs/gui_client_TIMESTAMP.log)"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode (equivalent to --log-level DEBUG)"
    )
    
    parser.add_argument(
        "--simple",
        action="store_true",
        help="Force simple interface (disable Rich GUI)"
    )
    
    args = parser.parse_args()
    
    if args.debug:
        args.log_level = "DEBUG"
    
    # Setup logging
    log_file = setup_logging(args.log_level, args.log_file)
    
    # Choose interface based on availability and user preference
    use_rich = RICH_AVAILABLE and not args.simple
    
    async def run_client():
        if use_rich:
            print("🎨 Loading Rich GUI interface...")
            try:
                from src.gui_client import AdaGUIClient
                client = AdaGUIClient()
                await client.run(args.room)
            except Exception as e:
                print(f"❌ Rich GUI failed: {e}")
                print("🔄 Falling back to simple interface...")
                use_rich = False
        
        if not use_rich:
            print("📟 Using simple terminal interface...")
            client = SimpleAdaClient()
            await client.run(args.room)
    
    try:
        asyncio.run(run_client())
    except KeyboardInterrupt:
        print("\n\n👋 Client stopped")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()