# Technical Context: Ada Voice Agent

## Technology Stack

### Core Technologies
- **Language**: Python 3.x
- **Framework**: LiveKit Agents Framework
- **Audio**: LiveKit WebRTC + PyAudio
- **Package Management**: Nix Flakes for reproducible builds
- **Environment**: devenv for development shell

### Local AI Components
- **STT**: faster-whisper (local Whisper implementation)
- **LLM**: Ollama (local model server with OpenAI-compatible API)
- **TTS**: Piper TTS (fast neural voice synthesis)
- **VAD**: Silero VAD (via LiveKit plugins)

### LiveKit Ecosystem
```python
# Core LiveKit imports
from livekit import api, rtc, agents
from livekit.agents import stt, tts, llm
from livekit.plugins import openai, silero
```

### Key Dependencies
```txt
# Core LiveKit
livekit
livekit-agents
livekit-plugins-openai
livekit-plugins-silero

# Audio Processing  
scipy
numpy
pyaudio

# Local AI Models
faster-whisper
piper-tts

# Utilities
python-dotenv
```

## Development Environment

### Nix Flakes Setup
- **devenv.nix**: Defines development environment
- **devenv.yaml**: Environment configuration
- **flake.nix**: Nix flake for reproducible builds
- **.envrc**: direnv integration for auto-activation

### Prerequisites
1. **Nix with flakes enabled**
2. **LiveKit server** (local or remote)
3. **Ollama server** with model (llama3.2:3b recommended)
4. **Piper voice models** downloaded to `models/` directory

### Environment Variables
```bash
# LiveKit Configuration
LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=devkey
LIVEKIT_API_SECRET=secret

# Local Models
WHISPER_MODEL=base                    # tiny|base|small|medium|large
PIPER_MODEL_PATH=models/en_US-amy-low.onnx
PIPER_CONFIG_PATH=models/en_US-amy-low.onnx.json
OLLAMA_MODEL=llama3.2:3b

# Optional
AGENT_NAME=Ada
LOG_LEVEL=INFO
```

## Architecture Constraints

### Audio Format Requirements
- **Input**: 48kHz from LiveKit clients
- **STT Processing**: 16kHz (Whisper requirement)
- **TTS Output**: 22kHz (Piper default) → 48kHz (LiveKit requirement)
- **Format**: 16-bit PCM, mono channel

### Performance Considerations
- **Memory**: Whisper models range from 39MB (tiny) to 2.9GB (large-v3)
- **CPU**: Real-time processing requires multi-core for concurrent STT/TTS
- **Latency**: Target <1 second voice-to-voice response time
- **Concurrency**: AsyncIO-based with thread pool for CPU-intensive tasks

### Integration Patterns

#### Ollama Integration
```python
# OpenAI-compatible HTTP API
self.llm = openai.LLM(
    model="llama3.2:3b",
    base_url="http://localhost:11434/v1", 
    api_key="ollama"  # Required but unused
)
```

#### Piper Integration
```bash
# Command-line subprocess execution
piper --model models/voice.onnx --config models/voice.json \
      --speaker 0 --output-file output.wav < input.txt
```

#### LiveKit Agent Pattern
```python
# Agent worker registration
agents.cli.run_app(agents.WorkerOptions(
    entrypoint_fnc=entrypoint
))
```

## File Organization

### Source Structure
```
src/
├── main.py          # Entry point with agents.cli integration
├── local_stt.py     # Whisper STT wrapper for LiveKit
└── local_tts.py     # Piper TTS wrapper for LiveKit

scripts/
├── agent.py         # Main agent implementation
└── client.py        # Test client with status indicators

models/              # TTS voice models (not in git)
tests/              # Unit tests
docs/               # Documentation (needs cleanup)
```

### Runtime Files
- `run_ada.py`: Clean agent runner with logging filters
- `test_ada_quick.py`: Quick validation script
- `.env`: Local environment variables (not in git)
- Various log files from testing

## Development Workflow

### Setup Commands
```bash
# Enter development environment
nix develop

# Or with direnv
cd project-dir  # Auto-activates via .envrc

# Run agent
python run_ada.py [room-name]

# Run tests
python test_ada_quick.py
```

### Testing Pattern
1. Start agent in one terminal
2. Connect client in another terminal  
3. Monitor status indicators for pipeline health
4. Use logging filters to reduce noise

## Known Technical Challenges

### Audio Resampling
- Multiple sample rate conversions required
- scipy.signal.resample used for quality
- Timing coordination critical for natural speech

### Logging Noise
- LiveKit IPC generates pickle serialization errors
- `run_ada.py` includes comprehensive log filtering
- Filters 50+ error patterns while preserving useful logs

### ChatContext API Changes
- Recent LiveKit changes required ChatMessage format updates
- Content must be list of strings, not direct strings
- Agent handles both streaming and non-streaming LLM responses

### Turn-taking Complexity
- Voice activity detection with multiple thresholds
- Anti-echo logic to prevent self-interruption
- Pre-buffering for smooth conversation starts

This technical foundation supports a robust, local-first voice AI system with production-ready reliability.