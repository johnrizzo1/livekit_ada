#!/usr/bin/env python3
"""Enhanced Ada Voice Client with Rich interface and proper input handling"""
import asyncio
import threading
import time
from datetime import datetime
import argparse
import logging
import os
import queue
from typing import List, Tuple

# Rich imports for UI
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
from rich import box

# Local imports
from src.client import VoiceClient, StatusDisplay


class ChatInterface:
    """Chat interface with proper input handling"""
    
    def __init__(self):
        self.conversation_history: List[Tuple[str, str, str]] = []  # (role, text, timestamp)
        self.status_text = "📡 Connecting..."
        self.text_input_queue = queue.Queue()
        self.console = Console()
        self.layout = Layout()
        self.client = None
        self.max_messages = 20
        
        self.create_layout()
        
    def create_layout(self):
        """Create the layout structure"""
        self.layout.split_column(
            Layout(name="header", size=3),    # Title and status
            Layout(name="main"),              # Conversation area
            Layout(name="footer", size=5)     # Controls and input area
        )
        
    def get_header_panel(self):
        """Create header panel with title and status"""
        header_text = Text()
        header_text.append("🎯 Ada Voice Client - Enhanced Chat", style="bold blue")
        header_text.append(f"\n{self.status_text}", style="green")
        
        return Panel(
            header_text,
            title="Status",
            border_style="blue",
            box=box.ROUNDED
        )
        
    def get_conversation_panel(self):
        """Create conversation panel with message history"""
        if not self.conversation_history:
            content = Text(
                "💭 Conversation will appear here...\n\n"
                "🎙️ Speak to Ada or use the input commands below", 
                style="dim", justify="center")
        else:
            content = Text()
            # Show recent messages
            recent_messages = self.conversation_history[-self.max_messages:]
            for role, text, timestamp in recent_messages:
                if role == "user":
                    content.append(f"[{timestamp}] ", style="dim")
                    content.append("👤 You: ", style="cyan bold")
                    content.append(f"{text}\n", style="cyan")
                elif role == "agent":
                    content.append(f"[{timestamp}] ", style="dim")
                    content.append("🤖 Ada: ", style="green bold")
                    content.append(f"{text}\n", style="green")
                elif role == "system":
                    content.append(f"[{timestamp}] ", style="dim")
                    content.append("ℹ️  ", style="yellow")
                    content.append(f"{text}\n", style="yellow")
                content.append("\n")
        
        return Panel(
            content,
            title="Conversation",
            border_style="white",
            box=box.ROUNDED
        )
        
    def get_footer_panel(self):
        """Create footer panel with instructions"""
        footer_text = Text()
        footer_text.append("📝 INPUT METHODS:\n", style="bold yellow")
        footer_text.append("  🎤 Voice: ", style="green")
        footer_text.append("Speak naturally (default)\n", style="white")
        footer_text.append("  💬 Text: ", style="cyan")
        footer_text.append("Press 't' + Enter, then type message + Enter\n", style="white")
        footer_text.append("  📋 Commands: ", style="magenta")
        footer_text.append("'h' for help, 'q' to quit", style="white")
        
        return Panel(
            footer_text,
            title="Controls",
            border_style="cyan",
            box=box.ROUNDED
        )
        
    def update_layout(self):
        """Update the layout with current content"""
        self.layout["header"].update(self.get_header_panel())
        self.layout["main"].update(self.get_conversation_panel())
        self.layout["footer"].update(self.get_footer_panel())
        
    def add_message(self, role: str, text: str):
        """Add a message to the conversation history"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.conversation_history.append((role, text, timestamp))
        
    def update_status(self, status: str):
        """Update the status text"""
        self.status_text = status


class EnhancedVoiceClient(VoiceClient):
    """Enhanced voice client with chat integration"""
    
    def __init__(self, status, chat_interface, conversation_callback=None):
        super().__init__(status, conversation_callback)
        self.chat_interface = chat_interface
        
    async def send_text_message(self, message: str):
        """Override to show sent messages in chat"""
        await super().send_text_message(message)
        self.chat_interface.add_message("user", f"💬 {message}")


def setup_logging(log_level: str) -> str:
    """Setup logging configuration"""
    if not os.path.exists("logs"):
        os.makedirs("logs")
    
    log_file = (f"logs/client_enhanced_"
               f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    
    # Configure logging - file only, suppress all console output
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file)
        ],
        force=True  # Force reconfiguration to override any existing handlers
    )
    
    # Suppress all logging to console by setting root logger handlers
    root_logger = logging.getLogger()
    root_logger.handlers = [logging.FileHandler(log_file)]
    
    # Also suppress specific loggers that might be noisy
    logging.getLogger("livekit").setLevel(logging.WARNING)
    logging.getLogger("websockets").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    
    return log_file


async def main():
    """Enhanced main function with chat interface"""
    parser = argparse.ArgumentParser(
        description="Ada Voice Client - Enhanced Chat")
    parser.add_argument("--room", default="test-room", 
                       help="LiveKit room name")
    parser.add_argument(
        "--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO", help="Logging level")
    
    args = parser.parse_args()
    
    # Setup logging
    log_file = setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    # Create chat interface
    chat_interface = ChatInterface()
    
    # Create conversation callback to capture voice interactions
    def conversation_callback(role, text):
        """Callback to capture conversation from voice client"""
        if role == "user":
            chat_interface.add_message("user", f"🎤 {text}")
        elif role == "agent":
            chat_interface.add_message("agent", text)
    
    # Create enhanced status display and client
    status = StatusDisplay()
    client = EnhancedVoiceClient(status, chat_interface, conversation_callback)
    chat_interface.client = client
    
    # Input handling with proper terminal management
    def handle_input():
        """Handle keyboard input in a separate thread"""
        console = Console()
        
        # Print instructions outside Rich interface
        console.print("\n" + "="*60, style="cyan")
        console.print("🎯 ADA VOICE CLIENT - ENHANCED CHAT", style="bold blue")
        console.print("="*60, style="cyan")
        console.print(f"Room: {args.room}", style="white")
        console.print(f"Log file: {log_file}", style="dim")
        console.print("="*60, style="cyan")
        console.print()
        console.print("INPUT COMMANDS:", style="bold yellow")
        console.print("  t + Enter  - Enter text input mode", style="cyan")
        console.print("  h + Enter  - Show help", style="green")
        console.print("  q + Enter  - Quit", style="red")
        console.print("  Ctrl+C     - Force quit", style="red")
        console.print("="*60, style="cyan")
        console.print()
        
        import sys
        import select
        import termios
        import tty
        
        def get_char():
            """Get a single character from stdin"""
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(sys.stdin.fileno())
                ch = sys.stdin.read(1)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            return ch, old_settings
        
        try:
            while True:
                # Check for input (non-blocking)
                if select.select([sys.stdin], [], [], 0.1) == ([sys.stdin], [], []):
                    char, old_settings = get_char()
                    
                    if char == 't':
                        # Text input mode
                        console.print("\n📝 TEXT INPUT MODE - Type your message:", 
                                    style="cyan bold")
                        console.print("(Press Enter to send, Ctrl+C to cancel)", 
                                    style="dim")
                        try:
                            # Restore normal terminal for input
                            termios.tcsetattr(sys.stdin.fileno(), 
                                            termios.TCSADRAIN, old_settings)
                            message = input("Message: ").strip()
                            if message:
                                # Send the message
                                asyncio.run_coroutine_threadsafe(
                                    client.send_text_message(message), 
                                    asyncio.get_event_loop()
                                )
                                console.print(f"✅ Sent: {message}", 
                                             style="green")
                        except (EOFError, KeyboardInterrupt):
                            console.print("❌ Cancelled", style="red")
                    
                    elif char == 'h':
                        console.print("\n📋 HELP:", style="yellow bold")
                        console.print("  Voice Input: Just speak naturally", 
                                    style="green")
                        console.print("  Text Input: Press 't' then Enter, type message", 
                                    style="cyan")
                        console.print("  Help: Press 'h' then Enter", 
                                    style="yellow")
                        console.print("  Quit: Press 'q' then Enter or Ctrl+C", 
                                    style="red")
                    
                    elif char == 'q':
                        console.print("\n👋 Quitting...", style="yellow")
                        break
                        
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            console.print("\n👋 Interrupted, quitting...", style="yellow")
    
    try:
        chat_interface.add_message(
            "system", f"Starting Ada Voice Client (Room: {args.room})")
        chat_interface.add_message("system", f"Logs: {log_file}")
        
        # Start input handler in separate thread
        input_thread = threading.Thread(target=handle_input, daemon=True)
        input_thread.start()
        
        # Create live display with slower refresh to reduce conflicts
        with Live(chat_interface.layout, refresh_per_second=2, screen=True):
            chat_interface.update_status("🔗 Connecting to Ada...")
            chat_interface.update_layout()
            
            # Connect to Ada
            await client.connect(args.room)
            
            chat_interface.update_status("✅ Connected - Voice & Text Ready")
            chat_interface.add_message(
                "system",
                "Connected! You can now speak to Ada or use text input")
            chat_interface.update_layout()
            
            # Main loop with reduced update frequency
            while (client.room.connection_state == 
                   client.room.ConnectionState.CONN_CONNECTED):
                # Update display less frequently
                chat_interface.update_layout()
                await asyncio.sleep(0.5)  # 2fps instead of 4fps
                
    except KeyboardInterrupt:
        chat_interface.add_message("system", "Disconnecting...")
        chat_interface.update_layout()
    except Exception as e:
        logger.error("Error: %s", e)
        chat_interface.add_message("system", f"Error: {e}")
        chat_interface.update_layout()
    finally:
        if hasattr(client, 'disconnect'):
            await client.disconnect()
        chat_interface.add_message("system", "Client stopped")


if __name__ == "__main__":
    asyncio.run(main())