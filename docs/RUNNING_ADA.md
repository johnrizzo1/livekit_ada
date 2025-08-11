# Running Ada - LiveKit Voice Agent

## Prerequisites

1. **LiveKit Server** running (local or remote)
2. **Ollama** running with your chosen model
3. **Whisper** model will auto-download on first run
4. **Piper** voice model files downloaded

## Quick Start

### 1. Test Components
```bash
python scripts/test_ada.py
```

This will verify:
- All required environment variables
- Piper model files exist
- Ollama is running with the correct model
- All imports work correctly

### 2. Start the Agent

#### Development Mode (recommended for testing):
```bash
python scripts/ada_agent.py dev
```

#### Production Mode:
```bash
python scripts/ada_agent.py start
```

#### Connect to Specific Room:
```bash
python scripts/ada_agent.py connect <room-name>
```

### 3. Connect a Client
In another terminal:
```bash
python scripts/client.py [room-name]
```

## Status Indicators

The agent displays real-time pipeline status:

- 🔇 Low audio level (< 200)
- 🔉 Medium audio level (200-1000)  
- 🔊 High audio level (> 1000)

Pipeline states:
- ⚪ LISTENING - Waiting for speech
- 🔴 RECORDING - Detecting speech
- 🎙️ TRANSCRIBING - Converting speech to text
- 🤔 THINKING - LLM processing
- 📢 SPEAKING - TTS output

## Configuration

Edit `.env` file to change:
- `WHISPER_MODEL` - Whisper model size (tiny, base, small, medium, large)
- `OLLAMA_MODEL` - Ollama model name
- `PIPER_MODEL_PATH` - Path to Piper .onnx file
- `PIPER_CONFIG_PATH` - Path to Piper .json config

## Troubleshooting

### "Cannot connect to Ollama"
Make sure Ollama is running:
```bash
ollama serve
```

### "Model file missing"  
Download Piper models from: https://github.com/rhasspy/piper/releases

### "No audio input/output"
Check your default audio devices and LiveKit room settings.

## Architecture

The new Ada agent uses:
- LiveKit `Agent` class for conversation logic
- LiveKit `AgentSession` for voice pipeline management
- Local Whisper STT wrapped with LiveKit interface
- Local Piper TTS wrapped with LiveKit interface
- Ollama LLM via OpenAI-compatible API
- Silero VAD for voice activity detection
- Event-driven status indicators