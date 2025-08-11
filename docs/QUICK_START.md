# Quick Start Guide - Local Voice Agent

This guide will help you get the local voice agent running quickly.

## Prerequisites

1. **Ollama** - Local LLM server
   ```bash
   # Install from https://ollama.ai
   ollama serve
   ollama pull llama3.2:3b
   ```

2. **Piper Voice Model** - Already downloaded in `models/`

3. **LiveKit Server** - Configure in `.env`

## Running the Agent

### Step 1: Start the Agent
```bash
python scripts/local_voice_agent_final.py start
```

You should see:
```
🔍 Checking local services...
✅ All services ready!
INFO - registered worker
```

### Step 2: Connect a Client

Option A - Debug Client (recommended for testing):
```bash
python scripts/connect_debug_client.py
```

Option B - Simple Client:
```bash
python scripts/connect_to_agent.py
```

Option C - Web Interface:
```bash
python -m http.server 8080
# Open http://localhost:8080/scripts/web_client.html
```

## How It Works

1. **Audio Flow**:
   - User speaks → Whisper STT → Text
   - Text → Ollama LLM → Response
   - Response → Piper TTS → Audio (16kHz)
   - Audio resampled to 48kHz → LiveKit → User

2. **Key Features**:
   - Completely offline operation
   - Low latency local processing
   - Proper audio timing (48kHz output)
   - Voice activity detection

## Troubleshooting

### Agent doesn't join room
- Make sure you connect a client first
- The agent auto-joins when participants connect

### Audio plays slowly
- Use the `local_voice_agent_final.py` which includes 48kHz resampling
- Check debug client output for timing ratios

### No response from agent
- Check Ollama is running: `curl http://localhost:11434/api/tags`
- Verify Whisper model is loaded (check logs)
- Ensure microphone permissions are granted

## Configuration

Edit `.env` to customize:
```bash
# LLM Model
OLLAMA_MODEL=llama3.2:3b  # Or mistral, llama2, etc.

# STT Model  
WHISPER_MODEL=base  # tiny, base, small, medium, large

# TTS Voice
PIPER_MODEL_PATH=models/en_US-amy-low.onnx
```

## Performance Tips

1. Use smaller models for lower latency:
   - Whisper: `tiny` or `base`
   - Ollama: `llama3.2:3b` or `phi`

2. Run on GPU if available (automatic detection)

3. Adjust VAD sensitivity for better turn detection

## Next Steps

- Try different voices: Download from [Piper Voices](https://github.com/rhasspy/piper/blob/master/VOICES.md)
- Experiment with different LLMs in Ollama
- Customize the assistant personality in the code