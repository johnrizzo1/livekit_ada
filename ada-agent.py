#!/usr/bin/env python3
"""
Ada - Local Voice AI Agent
A fully local, privacy-first voice AI agent built with LiveKit.
"""
import argparse
import sys
import asyncio
import logging
from pathlib import Path
from datetime import datetime

# Ensure src is in path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.agent import run_agent


def setup_logging(log_level: str = "INFO", log_file: str = None):
    """Setup logging configuration"""
    if not log_file:
        log_file = f"logs/agent_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    # Create logs directory
    Path("logs").mkdir(exist_ok=True)

    # Configure logging to file
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            # Keep minimal console output for status
            logging.StreamHandler(sys.stdout) if log_level == "DEBUG" else logging.NullHandler()
        ]
    )

    return log_file


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Ada - Local Voice AI Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # Start agent with default room
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
        help="Log file path (default: logs/agent_TIMESTAMP.log)"
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode (equivalent to --log-level DEBUG)"
    )

    args = parser.parse_args()

    if args.debug:
        args.log_level = "DEBUG"

    # Setup logging
    log_file = setup_logging(args.log_level, args.log_file)

    # Print startup banner
    print("🚀 Ada - Local Voice AI Agent")
    print("=" * 50)
    print(f"Room: {args.room}")
    print(f"Log Level: {args.log_level}")
    print(f"Log File: {log_file}")
    print("=" * 50)
    print()
    print("🔧 Initializing components...")
    
    try:
        # Run the agent
        asyncio.run(run_agent(args.room))
    except KeyboardInterrupt:
        print("\n\n⏹️  Shutting down Ada Agent...")
        print("✅ Agent stopped")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()