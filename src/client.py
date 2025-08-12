#!/usr/bin/env python3
"""Voice client with comprehensive status indicators"""
import asyncio
import sys
from pathlib import Path
import logging
from livekit import api, rtc
import pyaudio
import numpy as np
from dotenv import load_dotenv
import os
import threading
import queue
import time

from .status_display import StatusDisplay
from .voice_client import VoiceClient

load_dotenv()

# Logger will be configured by main CLI
logger = logging.getLogger(__name__)


async def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Voice client with indicators")
    parser.add_argument("room", nargs="?", default="test-room",
                       help="Room name")
    args = parser.parse_args()
    
    print("\n🎯 VOICE CLIENT WITH STATUS INDICATORS")
    print("="*60)
    print(f"Room: {args.room}")
    print("="*60)
    
    status = StatusDisplay()
    client = VoiceClient(status)
    
    try:
        await client.connect(args.room)
        
        # Keep running
        while (client.room.connection_state ==
               rtc.ConnectionState.CONN_CONNECTED):
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\nExiting...")
    finally:
        await client.disconnect()
        print("\n👋 Disconnected")


if __name__ == "__main__":
    asyncio.run(main())