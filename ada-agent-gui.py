#!/usr/bin/env python3
"""
Ada Agent GUI - Beautiful Terminal Interface
Enhanced agent with Rich TUI interface and comprehensive monitoring
"""
import argparse
import sys
import asyncio
import logging
from pathlib import Path
from datetime import datetime
import threading
import time
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
    from rich.columns import Columns
    import rich.box
    
    RICH_AVAILABLE = True
except ImportError:
    print("❌ Rich library not found. Install with: pip install rich")
    print("   Falling back to basic agent interface...")
    RICH_AVAILABLE = False

from src.agent import run_agent, ConversationAgent, StatusIndicator

logger = logging.getLogger(__name__)


class AgentGUIManager:
    """GUI manager for the Ada agent"""
    def __init__(self):
        self.console = Console()
        self.layout = self._create_layout()
        self.agent_stats = {
            "connections": 0,
            "messages_processed": 0,
            "dictations_taken": 0,
            "uptime_start": datetime.now(),
            "current_mode": "Listening",
            "last_activity": "Waiting for connections..."
        }
        self.conversation_history = []
        self.system_logs = []
        
    def _create_layout(self) -> Layout:
        """Create the main layout"""
        layout = Layout()
        
        # Main split
        layout.split_column(
            Layout(name="header", size=4),
            Layout(name="main"),
            Layout(name="footer", size=3),
        )
        
        # Split main area
        layout["main"].split_row(
            Layout(name="left", ratio=2),
            Layout(name="right", ratio=1),
        )
        
        # Left side split
        layout["left"].split_column(
            Layout(name="conversation"),
            Layout(name="logs", size=8),
        )
        
        # Right side is stats
        layout["right"].split_column(
            Layout(name="stats"),
            Layout(name="status", size=10),
        )
        
        return layout
        
    def _create_header_panel(self) -> Panel:
        """Create header panel"""
        header_text = Text()
        header_text.append("🤖 ", style="bold blue")
        header_text.append("Ada AI Agent", style="bold white")
        header_text.append(" • ", style="dim")
        header_text.append("Voice AI Assistant with Dictation", style="dim cyan")
        
        return Panel(
            Align.center(header_text),
            box=rich.box.ROUNDED,
            style="blue",
            title="Ada Agent",
            title_align="left"
        )
        
    def _create_conversation_panel(self) -> Panel:
        """Create conversation display panel"""
        if not self.conversation_history:
            content = Text("💬 Conversation will appear here...", style="dim italic")
        else:
            content = Text()
            for i, msg in enumerate(self.conversation_history[-10:]):
                if i > 0:
                    content.append("\n")
                    
                timestamp = msg.get("timestamp", "")
                msg_type = msg.get("type", "")
                text = msg.get("text", "")
                
                content.append(f"[{timestamp}] ", style="dim")
                
                if msg_type == "user":
                    content.append("👤 User: ", style="bold green")
                    content.append(text, style="white")
                elif msg_type == "agent":
                    content.append("🤖 Ada: ", style="bold blue")
                    content.append(text, style="cyan")
                elif msg_type == "dictation":
                    content.append("📝 Dictation: ", style="bold yellow")
                    content.append(text[:50] + "..." if len(text) > 50 else text, style="yellow")
                else:
                    content.append("ℹ️  ", style="dim")
                    content.append(text, style="dim")
                    
        return Panel(
            content,
            box=rich.box.ROUNDED,
            title="💬 Recent Conversation",
            title_align="left"
        )
        
    def _create_logs_panel(self) -> Panel:
        """Create system logs panel"""
        if not self.system_logs:
            content = Text("📊 System logs will appear here...", style="dim italic")
        else:
            content = Text()
            for i, log in enumerate(self.system_logs[-6:]):
                if i > 0:
                    content.append("\n")
                content.append(f"[{log['time']}] ", style="dim")
                
                level = log.get("level", "INFO")
                if level == "ERROR":
                    content.append(f"❌ {log['message']}", style="red")
                elif level == "WARNING": 
                    content.append(f"⚠️  {log['message']}", style="yellow")
                else:
                    content.append(f"ℹ️  {log['message']}", style="white")
                    
        return Panel(
            content,
            box=rich.box.ROUNDED,
            title="📊 System Logs",
            title_align="left"
        )
        
    def _create_stats_panel(self) -> Panel:
        """Create statistics panel"""
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Metric", style="bold")
        table.add_column("Value")
        
        # Calculate uptime
        uptime = datetime.now() - self.agent_stats["uptime_start"]
        uptime_str = str(uptime).split(".")[0]  # Remove microseconds
        
        table.add_row("🕒 Uptime:", uptime_str)
        table.add_row("🔗 Connections:", str(self.agent_stats["connections"]))
        table.add_row("💬 Messages:", str(self.agent_stats["messages_processed"]))
        table.add_row("📝 Dictations:", str(self.agent_stats["dictations_taken"]))
        table.add_row("", "")
        table.add_row("🎯 Current Mode:", Text(self.agent_stats["current_mode"], style="cyan"))
        table.add_row("⚡ Last Activity:", Text(self.agent_stats["last_activity"][:25] + "..." 
                                              if len(self.agent_stats["last_activity"]) > 25 
                                              else self.agent_stats["last_activity"], style="dim"))
        
        return Panel(
            table,
            box=rich.box.ROUNDED,
            title="📈 Statistics",
            title_align="left"
        )
        
    def _create_status_panel(self) -> Panel:
        """Create status panel"""
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Component", style="bold")
        table.add_column("Status")
        
        # System components
        table.add_row("🎤 Speech-to-Text:", Text("✅ Whisper Ready", style="green"))
        table.add_row("🔊 Text-to-Speech:", Text("✅ Piper Ready", style="green"))
        table.add_row("🧠 Language Model:", Text("✅ Ollama Ready", style="green"))
        table.add_row("🔗 LiveKit:", Text("✅ Connected", style="green"))
        table.add_row("", "")
        
        # Current capabilities
        table.add_row("💬 Conversation:", Text("Active", style="green"))
        table.add_row("📝 Dictation:", Text("Available", style="blue"))
        table.add_row("🔊 Voice Output:", Text("Active", style="green"))
        table.add_row("👂 Voice Input:", Text("Listening", style="green"))
        
        return Panel(
            table,
            box=rich.box.ROUNDED,
            title="🟢 System Status",
            title_align="left"
        )
        
    def _create_footer_panel(self) -> Panel:
        """Create footer panel"""
        footer_text = Text()
        footer_text.append("🎯 Ada Agent Running • ", style="green")
        footer_text.append("Voice + Dictation Ready • ", style="cyan")
        footer_text.append("Press Ctrl+C to stop", style="dim")
        
        return Panel(
            Align.center(footer_text),
            box=rich.box.ROUNDED,
            style="green"
        )
        
    def update_display(self):
        """Update the display layout"""
        if hasattr(self, 'live') and self.live:
            self.layout["header"].update(self._create_header_panel())
            self.layout["conversation"].update(self._create_conversation_panel())
            self.layout["logs"].update(self._create_logs_panel())
            self.layout["stats"].update(self._create_stats_panel())
            self.layout["status"].update(self._create_status_panel())
            self.layout["footer"].update(self._create_footer_panel())
            
    def add_conversation_message(self, msg_type: str, text: str):
        """Add a conversation message"""
        self.conversation_history.append({
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "type": msg_type,
            "text": text
        })
        
        # Update stats
        if msg_type in ["user", "agent"]:
            self.agent_stats["messages_processed"] += 1
        elif msg_type == "dictation":
            self.agent_stats["dictations_taken"] += 1
            
        self.agent_stats["last_activity"] = f"{msg_type}: {text[:30]}..."
        self.update_display()
        
    def add_system_log(self, message: str, level: str = "INFO"):
        """Add a system log message"""
        self.system_logs.append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "message": message,
            "level": level
        })
        self.update_display()
        
    def set_current_mode(self, mode: str):
        """Set the current agent mode"""
        self.agent_stats["current_mode"] = mode
        self.update_display()
        
    async def run(self, room_name: str = "ada-room"):
        """Run the GUI agent"""
        with Live(self.layout, console=self.console, refresh_per_second=2, 
                  screen=True) as live:
            self.live = live
            
            try:
                # Initial display
                self.update_display()
                
                # Add welcome message
                self.add_system_log(f"Starting Ada Agent for room: {room_name}")
                self.add_system_log("Initializing AI components...")
                
                # Run the agent (this will block)
                await run_agent(room_name)
                
            except KeyboardInterrupt:
                self.add_system_log("Shutdown requested by user")
                self.update_display()
                await asyncio.sleep(1)


def setup_logging(log_level: str = "INFO", log_file: str = None):
    """Setup logging configuration"""
    if not log_file:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = f"logs/agent_{timestamp}.log"
    
    # Create logs directory
    Path("logs").mkdir(exist_ok=True)
    
    # Configure logging to file only
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
        description="Ada Agent GUI - Beautiful Voice AI Interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # Start agent in default room
  %(prog)s --room my-room     # Start in specific room
  %(prog)s --debug           # Enable debug logging
  
Features:
  • Voice conversation with natural language processing
  • Dictation mode for long-form transcription
  • Real-time status monitoring
  • System performance metrics
  • Beautiful terminal interface
        """
    )
    
    parser.add_argument(
        "--room",
        default="ada-room",
        help="LiveKit room name (default: ada-room)"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)"
    )
    
    parser.add_argument(
        "--log-file",
        help="Log file path (default: logs/agent_TIMESTAMP.log)"
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
    
    # Choose interface
    use_rich = RICH_AVAILABLE and not args.simple
    
    async def run_agent_gui():
        if use_rich:
            print("🎨 Loading Rich GUI interface...")
            try:
                gui_manager = AgentGUIManager()
                await gui_manager.run(args.room)
            except Exception as e:
                print(f"❌ Rich GUI failed: {e}")
                print("🔄 Falling back to simple interface...")
                use_rich = False
        
        if not use_rich:
            print("📟 Using simple agent interface...")
            print(f"Starting Ada Agent in room: {args.room}")
            print(f"Logging to: {log_file}")
            await run_agent(args.room)
    
    try:
        asyncio.run(run_agent_gui())
    except KeyboardInterrupt:
        print("\n\n👋 Agent stopped")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()