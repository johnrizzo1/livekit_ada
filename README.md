# Ada - Local Voice AI Agent

A fully local, privacy-first voice AI agent built with LiveKit for real-time conversations without any cloud dependencies.

## Features

- **Complete Privacy**: All processing happens locally - no data leaves your machine
- **Real-time Voice**: Sub-second voice-to-voice response times
- **Local AI Stack**: 
  - Speech-to-Text: Whisper (faster-whisper)
  - Text-to-Speech: Piper TTS
  - Language Model: Ollama
  - Voice Activity Detection: Silero VAD
- **LiveKit Native**: Built on LiveKit's agent framework for production reliability
- **Rich Monitoring**: Real-time status indicators and audio level monitoring

## Quick Start

1. **Prerequisites**
   - [Nix with flakes enabled](https://nixos.org/download.html)
   - [Ollama](https://ollama.ai) running with a model (e.g., `llama3.2:3b`)
   - LiveKit server (local or remote)

2. **Setup Environment**
   ```bash
   # Clone and enter project
   cd livekit_ada
   
   # Copy environment template
   cp .env.example .env
   
   # Edit .env with your settings
   # At minimum, set your LiveKit credentials and model paths
   ```

3. **Enter Development Environment**
   ```bash
   # Automatic with direnv (recommended)
   direnv allow
   
   # Or manually
   nix develop
   ```

4. **Run Ada**
   ```bash
   # Start the agent (cleans logging automatically)
   python run_ada.py [room-name]
   
   # Connect a test client in another terminal
   python scripts/client.py [room-name]
   ```

## How It Works

Ada uses an event-driven voice pipeline:

```
Audio Input → VAD → Whisper STT → Ollama LLM → Piper TTS → Audio Output
     ↓         ↓         ↓           ↓           ↓           ↓
Real-time status indicators show each processing stage
```

### Status Indicators
```
🔊 [████████░░] 5432 | 🔴 RECORDING → 🎙️ TRANSCRIBING → 🤔 THINKING → 📢 SPEAKING
```

- **Audio Level**: Visual meter shows microphone input strength
- **Pipeline States**: Clear indication of current processing stage
- **Turn Management**: Automatic detection of when to listen vs speak

## Configuration

Key environment variables in `.env`:

```bash
# LiveKit Connection
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

## Project Structure

```
.
├── memory-bank/          # Documentation and project knowledge
├── scripts/
│   ├── agent.py         # Main agent implementation 
│   └── client.py        # Test client with status indicators
├── src/
│   ├── main.py          # Entry point for agents.cli
│   ├── local_stt.py     # Whisper STT wrapper for LiveKit
│   └── local_tts.py     # Piper TTS wrapper for LiveKit
├── run_ada.py           # Clean agent runner (filters logging noise)
├── test_ada_quick.py    # Quick validation script
└── docs/                # Setup and usage guides
```

## Documentation

- **[Quick Start Guide](docs/QUICK_START.md)** - Fast setup for immediate use
- **[Running Ada](docs/RUNNING_ADA.md)** - Detailed operation instructions
- **[Audio Fix Summary](docs/AUDIO_FIX_SUMMARY.md)** - Audio resampling solution details

## Development

This project uses Nix flakes for reproducible development environments:

```bash
# Format code
nix run .#format

# Lint code  
nix run .#lint

# Type check
nix run .#typecheck

# Run tests
nix run .#test
```

## Architecture

Ada is built on proven architectural patterns:

- **Local-First**: Zero external dependencies during conversations
- **Event-Driven**: Async processing with proper turn-taking
- **LiveKit Native**: Full integration with LiveKit's agent framework
- **Multi-Rate Audio**: Handles format conversions (48kHz ↔ 16kHz ↔ 22kHz)
- **Status Transparency**: Rich monitoring for debugging and user feedback

## Performance

- **Latency**: ~800ms voice-to-voice (sub-second target achieved)
- **Memory**: ~200MB+ (depends on Whisper model size)
- **CPU**: Real-time on modern multi-core systems
- **Privacy**: Complete offline operation

## Why Local-First?

- **Privacy**: Your conversations never leave your machine
- **Latency**: No network round-trips for faster responses  
- **Reliability**: Works without internet connectivity
- **Cost**: No per-request API charges
- **Control**: Full ownership of your AI assistant

## Troubleshooting

Common issues and solutions:

1. **Agent won't start**: Ensure Ollama is running (`ollama serve`)
2. **No audio output**: Check Piper model files exist in `models/` 
3. **Slow responses**: Try smaller models (Whisper: `tiny`, Ollama: `llama3.2:3b`)
4. **Logging noise**: Use `run_ada.py` which filters multiprocessing errors

For detailed troubleshooting, see the documentation in `docs/`.

---

Ada represents a complete voice AI system that prioritizes privacy, performance, and local control. It demonstrates that sophisticated AI assistants can run entirely on personal hardware without compromising functionality or user experience.