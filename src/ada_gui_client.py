import asyncio
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable
import logging

from rich.console import Console
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.align import Align
from rich.columns import Columns
from rich.prompt import Prompt
import rich.box

from .conversation_manager import ConversationManager
from .voice_client import VoiceClient
from .gui_status_display import GUIStatusDisplay

logger = logging.getLogger(__name__)


class AdaGUIClient:
    """Main GUI client class"""
    def __init__(self):
        self.console = Console()
        self.conversation = ConversationManager()
        self.layout = self._create_layout()
        self.voice_client = None
        self.status_display = None
        self.input_handler = None
        self.live = None
        self.pending_input = ""
        
    def _create_layout(self) -> Layout:
        """Create the main layout"""
        layout = Layout()
        
        # Split into main sections
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="input", size=3),
        )
        
        # Split main into conversation and status
        layout["main"].split_row(
            Layout(name="conversation"),
            Layout(name="status", size=30),
        )
        
        return layout
        
    def _create_header_panel(self) -> Panel:
        """Create header panel"""
        header_text = Text()
        header_text.append("🎯 ", style="bold blue")
        header_text.append("Ada Voice & Text Client", style="bold white")
        header_text.append(" • ", style="dim")
        header_text.append("Voice + Text Interface", style="dim cyan")
        
        return Panel(
            Align.center(header_text),
            box=rich.box.ROUNDED,
            style="blue",
            title="Ada Client",
            title_align="left"
        )
        
    def _create_conversation_panel(self) -> Panel:
        """Create conversation display panel"""
        messages = self.conversation.get_recent_messages(15)
        
        if not messages:
            content = Text("💬 Conversation will appear here...", style="dim italic")
        else:
            content = Text()
            for i, msg in enumerate(messages):
                if i > 0:
                    content.append("\n")
                    
                # Timestamp
                content.append(f"[{msg['timestamp']}] ", style="dim")
                
                # Message based on type
                if msg['type'] == 'user':
                    content.append("👤 You: ", style="bold green")
                    content.append(msg['text'], style="white")
                elif msg['type'] == 'agent':
                    content.append("🤖 Ada: ", style="bold blue")  
                    content.append(msg['text'], style="cyan")
                else:  # system
                    content.append("ℹ️  ", style="yellow")
                    content.append(msg['text'], style="yellow dim")
                    
        return Panel(
            content,
            box=rich.box.ROUNDED,
            title="💬 Conversation",
            title_align="left",
            height=20
        )
        
    def _create_status_panel(self) -> Panel:
        """Create status panel"""
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Label", style="bold")
        table.add_column("Value")
        
        if self.status_display:
            # Connection status
            conn_color = "green" if "Connected" in self.status_display.connection_status else "yellow"
            table.add_row("🔗 Connection:", 
                         Text(self.status_display.connection_status, style=conn_color))
            
            # Microphone level
            mic_level = self.status_display.mic_level
            if mic_level < 300:
                mic_status = Text("🔇 Silent", style="dim")
            elif mic_level < 1000:
                mic_status = Text("🔉 Detecting", style="yellow")
            else:
                mic_status = Text("🔊 SPEAKING", style="green bold")
                
            table.add_row("🎤 Microphone:", mic_status)
            table.add_row("📊 Level:", f"{mic_level:,}")
            
            # Agent status
            if self.status_display.agent_speaking:
                agent_status = Text("🤖 SPEAKING", style="blue bold")
            else:
                agent_status = Text("👂 Listening", style="dim")
            table.add_row("🤖 Agent:", agent_status)
            
            # Audio meter
            meter_level = min(20, int(mic_level / 500))
            meter = "█" * meter_level + "░" * (20 - meter_level)
            table.add_row("📈 Audio:", Text(meter, style="green"))
            
        else:
            table.add_row("🔗 Connection:", Text("Initializing...", style="yellow"))
            
        # Add controls info
        table.add_row("", "")
        table.add_row("⌨️  Controls:", Text("Type & press Enter", style="dim"))
        table.add_row("🎤 Voice:", Text("Use microphone", style="dim"))
        table.add_row("🚪 Exit:", Text("Ctrl+C", style="dim"))
        
        return Panel(
            table,
            box=rich.box.ROUNDED,
            title="📊 Status",
            title_align="left"
        )
        
    def _create_input_panel(self) -> Panel:
        """Create input panel"""
        input_text = Text()
        input_text.append("💬 Type your message: ", style="bold")
        input_text.append(self.pending_input, style="white on blue")
        input_text.append("_", style="bold white blink")  # Cursor
        
        return Panel(
            input_text,
            box=rich.box.ROUNDED,
            title="✍️  Text Input",
            title_align="left",
            style="blue"
        )
        
    def _update_display(self):
        """Update the display layout"""
        if self.live:
            self.layout["header"].update(self._create_header_panel())
            self.layout["conversation"].update(self._create_conversation_panel())
            self.layout["status"].update(self._create_status_panel())
            self.layout["input"].update(self._create_input_panel())
            
    async def connect_voice(self, room_name: str):
        """Connect voice client"""
        self.status_display = GUIStatusDisplay(self._update_display)
        self.voice_client = VoiceClient(self.status_display, self.conversation)
        
        self.conversation.add_system_message(f"Connecting to room: {room_name}")
        await self.voice_client.connect(room_name)
        self.conversation.add_system_message("✅ Voice connection established")
        
    def handle_text_input(self, text: str):
        """Handle text input from user"""
        if not text.strip():
            return
            
        self.conversation.add_user_message(text)
        
        # Here you could add logic to send text to the agent
        # For now, just acknowledge the input
        self.conversation.add_system_message(f"Text message received: {text[:50]}...")
        
    async def run(self, room_name: str = "ada-room"):
        """Run the GUI client"""
        # Set up callbacks
        self.conversation.set_update_callback(self._update_display)
        
        with Live(self.layout, console=self.console, refresh_per_second=10, 
                  screen=True) as live:
            self.live = live
            
            try:
                # Initial display
                self._update_display()
                
                # Connect voice
                await self.connect_voice(room_name)
                
                # Start input handling
                self._start_input_handling()
                
                # Main loop
                while True:
                    await asyncio.sleep(0.1)
                    
            except KeyboardInterrupt:
                self.conversation.add_system_message("👋 Shutting down...")
                self._update_display()
                await asyncio.sleep(0.5)
                
    def _start_input_handling(self):
        """Start handling keyboard input"""
        def input_thread():
            while True:
                try:
                    # This is a simplified version - in practice you'd want
                    # proper async input handling with something like aioconsole
                    import sys
                    import select
                    
                    if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                        line = input()
                        if line:
                            self.handle_text_input(line)
                            
                except (EOFError, KeyboardInterrupt):
                    break
                except:
                    time.sleep(0.1)
                    
        threading.Thread(target=input_thread, daemon=True).start()
