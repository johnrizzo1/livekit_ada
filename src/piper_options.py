from dataclasses import dataclass

@dataclass
class PiperOptions:
    model_path: str = None
    config_path: str = None
    speaker_id: int = 0
    length_scale: float = 1.0
    noise_scale: float = 0.667
    noise_w: float = 0.8
    output_sample_rate: int = 16000