"""Whisper configuration options"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class WhisperOptions:
    model_size: str = "base"
    device: str = "auto"
    compute_type: str = "int8"
    language: str = "en"
    initial_prompt: Optional[str] = None
    vad_filter: bool = True
    vad_parameters: Optional[dict] = None