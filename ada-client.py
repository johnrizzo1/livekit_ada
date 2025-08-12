#!/usr/bin/env python3
"""
Ada Client - Voice Client with Clean Interface
A clean voice client for interacting with Ada agent.
"""
import argparse
import sys
import asyncio
import logging
from pathlib import Path
from datetime import datetime
import threading
import queue
import time
from typing import Optional

# Ensure src is in path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.gui_voice_client import CleanVoiceClient


class ConversationDisplay:
    """Manages the conversation display area"""
    def __init__(self):
        self.messages = []
        self.max_messages = 50
    
    def add_user_message(self, text: str):
        """Add user message to conversation"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.messages.append(f"[{timestamp}] 👤 You: {text}")
        self._trim_messages()
        self._refresh_display()
    
    def add_agent_message(self, text: str):
        """Add agent message to conversation"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.messages.append(f"[{timestamp}] 🤖 Ada: {text}")
        self._trim_messages()
        self._refresh_display()
    
    def add_system_message(self, text: str):
        """Add system message to conversation"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.messages.append(f"[{timestamp}] ℹ️  {text}")
        self._trim_messages()
        self._refresh_display()
    
    def _trim_messages(self):
        """Keep only the last N messages"""
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]
    
    def _refresh_display(self):
        """Refresh the conversation display"""
        # Clear the conversation area (lines 5-25)
        print("\033[5;1H")  # Move to line 5
        print("\033[J")     # Clear from cursor to end of screen
        
        # Display recent messages
        for message in self.messages[-15:]:  # Show last 15 messages
            print(message)
        
        # Return cursor to status area
        print("\033[2;1H")  # Move back to status line


class ImprovedStatusDisplay:
    """Enhanced status display with fixed positioning"""
    def __init__(self, conversation_display: ConversationDisplay):
        self.mic_level = 0
        self.is_speaking = False
        self.agent_speaking = False
        self.agent_listening = False
        self.connection_status = "Connecting..."
        self.last_update = 0
        self.conversation = conversation_display
        self.input_prompt = "💬 Type your message: "
        self.setup_display()
    
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
    
    def setup_display(self):
        """Setup the terminal display layout"""
        # Clear screen
        print("\033[2J")
        print("\033[H")
        
        # Header
        print("🎯 Ada Voice Client")
        print("-" * 60)
        print("Status: Initializing...")
        print("-" * 60)
        print("Conversation:")
        print()
        
        # Reserve space for conversation (lines 5-25)
        for _ in range(20):
            print()
        
        print("-" * 60)
        print("Audio Status: ")
        print(self.input_prompt, end="", flush=True)
    
    def _print_status(self):
        """Print status line at fixed position"""
        # Rate limit
        if time.time() - self.last_update < 0.1:
            return
        self.last_update = time.time()
        
        # Build status components
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
        status_line = (f"{mic_status} [{meter}] {self.mic_level:4d} | "
                      f"{agent_status} | {self.connection_status}")
        
        # Update status at fixed position (line 27)
        print(f"\033[27;1H\033[K{status_line[:60]}", end="", flush=True)
        
        # Return cursor to input line
        print(f"\033[28;{len(self.input_prompt)+1}H", end="", flush=True)


def setup_logging(log_level: str = "INFO", log_file: str = None):
    """Setup logging configuration"""
    if not log_file:
        log_file = f"logs/client_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
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


def handle_input(conversation: ConversationDisplay, client, loop):
    """Handle user input in a separate thread"""
    while True:
        try:
            user_input = input()
            if user_input.strip():
                conversation.add_user_message(user_input.strip())
                # Send text message to agent for LLM processing
                asyncio.run_coroutine_threadsafe(
                    client.send_text_message(user_input.strip()), loop
                )
        except (EOFError, KeyboardInterrupt):
            break


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Ada Voice Client - Clean Interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # Connect to default room
  %(prog)s --room my-room     # Connect to specific room
  %(prog)s --debug           # Enable debug logging
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
        help="Log file path (default: logs/client_TIMESTAMP.log)"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode (equivalent to --log-level DEBUG)"
    )
    
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Use Rich-based GUI interface (if available)"
    )
    
    args = parser.parse_args()
    
    if args.debug:
        args.log_level = "DEBUG"
    
    # Setup logging
    log_file = setup_logging(args.log_level, args.log_file)
    
    async def run_client():
        # Get the current event loop
        loop = asyncio.get_event_loop()
        
        # Setup display components
        conversation = ConversationDisplay()
        status = ImprovedStatusDisplay(conversation)
        client = CleanVoiceClient(status, conversation)
        
        # Start input handler thread (only in non-GUI mode)
        if not args.gui:
            input_thread = threading.Thread(
                target=handle_input,
                args=(conversation, client, loop),
                daemon=True
            )
            input_thread.start()
        else:
            conversation.add_system_message("📝 GUI Mode: Text input temporarily disabled")
            conversation.add_system_message("🎤 Voice input is active - speak to Ada")
        
        conversation.add_system_message(f"Connecting to room: {args.room}")
        conversation.add_system_message(f"Logging to: {log_file}")
        
        if args.gui:
            conversation.add_system_message("🎨 Enhanced GUI mode enabled")
        
        # Debug client state before connection
        conversation.add_system_message(f"🔍 Debug: client.connected = {client.connected}")
        
        try:
            conversation.add_system_message("🔗 Starting connection process...")
            await client.connect(args.room)
            conversation.add_system_message("✅ Voice connection established")
            conversation.add_system_message("💬 Text input ready - type and press Enter")
            
            # Debug client state after connection
            conversation.add_system_message(f"🔍 Debug: client.connected after connect = {client.connected}")
            
            # Wait a moment for connection to fully establish
            await asyncio.sleep(2)
            
            # Debug client state after wait
            conversation.add_system_message(f"🔍 Debug: client.connected after wait = {client.connected}")
            
            if not client.connected:
                conversation.add_system_message("❌ Connection failed to establish")
                conversation.add_system_message("⚠️ Will keep running anyway for debugging")
                # Don't return, keep running for debugging
            else:
                conversation.add_system_message("🟢 Client ready - connection stable")
            
            # Keep running with fallback and additional debugging
            conversation.add_system_message("🔄 Entering main client loop...")
            loop_count = 0
            try:
                while client.connected:
                    loop_count += 1
                    if loop_count % 10 == 0:  # Log every 10 seconds
                        conversation.add_system_message(f"🔄 Client running (loop {loop_count})")
                    await asyncio.sleep(1)
                    
                conversation.add_system_message("⚠️ Main loop exited - client.connected became False")
                
            except KeyboardInterrupt:
                raise
            except Exception as e:
                conversation.add_system_message(f"⚠️ Loop error: {e}, keeping client alive")
                # Fallback: keep running indefinitely
                fallback_count = 0
                while True:
                    fallback_count += 1
                    if fallback_count % 10 == 0:
                        conversation.add_system_message(f"🔄 Fallback mode (loop {fallback_count})")
                    await asyncio.sleep(1)
                
        except Exception as e:
            conversation.add_system_message(f"❌ Connection error: {e}")
            import traceback
            conversation.add_system_message(f"❌ Traceback: {traceback.format_exc()}")
    
    try:
        asyncio.run(run_client())
    except KeyboardInterrupt:
        print("\n\n👋 Disconnecting...")
        print("✅ Client stopped")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()