{ pkgs, lib, config, inputs, ... }:

{
  packages = with pkgs; [ 
    git
    piper-tts
    (python312.withPackages (ps: with ps; [
      # Core dependencies
      faster-whisper
      numpy
      scipy
      livekit-api
      livekit-protocol
      pytest
      pytest-asyncio
      python-dotenv
      black
      ruff
      mypy
      
      # Audio dependencies
      pyaudio
      soundfile
      librosa
      
      # Additional tools
      aiohttp
      requests
    ]))
  ];
  languages.python.enable = true;
  languages.python.venv.enable = true;
  languages.python.version = "3.12";
  languages.python.venv.requirements = ''
    livekit-agents[assemblyai,openai,rime,silero,turn-detector]
    livekit-plugins-noise-cancellation
  '';
  dotenv.enable = true;
  # See full reference at https://devenv.sh/reference/options/
}
