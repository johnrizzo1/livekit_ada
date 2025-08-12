#!/usr/bin/env python3
"""Simple Ada Voice Client - Back to Basics"""
import asyncio
import sys
import argparse
import logging
from datetime import datetime
from pathlib import Path
from src.client import VoiceClient, StatusDisplay

def setup_logging(log_level="INFO", log_file=None):
    """Setup logging configuration"""
    Path("logs").mkdir(exist_ok=True)
    
    if not log_file:
        log_file = f"logs/client_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return log_file

async def main():
    """Simple main function"""
    parser = argparse.ArgumentParser(description="Ada Voice Client - Simple Version")
    parser.add_argument("--room", default="ada-room", help="LiveKit room name")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], 
                       default="INFO", help="Logging level")
    
    args = parser.parse_args()
    
    # Setup logging
    log_file = setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    print("🎤 Ada Voice Client - Simple Version")
    print(f"📁 Logs: {log_file}")
    print(f"🏠 Room: {args.room}")
    print("=" * 50)
    
    try:
        # Create status display and client
        status = StatusDisplay()
        client = VoiceClient(status)
        
        print("🔗 Connecting to Ada...")
        await client.connect(args.room)
        print("✅ Connected! You can now speak to Ada.")
        print("💬 Press Ctrl+C to disconnect")
        
        # Keep running
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("\n👋 Disconnecting...")
    except Exception as e:
        logger.error(f"Error: {e}")
        print(f"❌ Error: {e}")
    finally:
        print("✅ Client stopped")

if __name__ == "__main__":
    asyncio.run(main())