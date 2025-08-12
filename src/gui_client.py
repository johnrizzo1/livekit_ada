#!/usr/bin/env python3
"""
Beautiful CLI GUI Client for Ada
Rich terminal interface with text input and conversation display
"""
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

from .voice_client import VoiceClient
from .status_display import StatusDisplay
from .ada_gui_client import AdaGUIClient

logger = logging.getLogger(__name__)


async def run_gui_client(room_name: str = "ada-room"):
    """Run the GUI client"""
    client = AdaGUIClient()
    await client.run(room_name)


if __name__ == "__main__":
    asyncio.run(run_gui_client())