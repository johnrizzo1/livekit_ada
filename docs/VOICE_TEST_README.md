# Voice Conversation Testing

This guide explains how to test voice conversations with your local AI agent.

## Prerequisites

1. **LiveKit Server**: Must be running at `ws://100.67.214.48:7880`
2. **Ollama**: Must be running with a model loaded (e.g., `llama3.2:3b`)
3. **Environment**: Enter devenv shell first: `devenv shell`

## Method 1: Two Terminal Approach (Recommended)

### Terminal 1 - Start the Agent
```bash
python -m src.agent_local start
```

Wait for these messages:
- "registered worker" - Agent connected to LiveKit
- "Using Ollama model" - LLM is ready

The agent takes ~30 seconds to initialize (loading Whisper STT model).

### Terminal 2 - Run Voice Test
```bash
python test_voice_final.py
```

This will:
1. Connect to a test room
2. Activate your microphone
3. Wait for the agent to join
4. The agent will greet you with audio
5. You can then have a conversation!

## Method 2: All-in-One Script

```bash
./run_voice_test.sh
```

This script starts the agent and test client together, but timing can be tricky.

## What to Expect

1. **Agent Greeting**: When the agent connects, it will say:
   "Hello! I am your local AI assistant running completely offline on your machine."

2. **Voice Interaction**: After the greeting, you can speak naturally. Try:
   - "Hello, can you hear me?"
   - "What's 2 plus 2?"
   - "Tell me a joke"

3. **Audio Output**: You'll hear the agent's responses through your speakers.

## Troubleshooting

### No Audio Output
- Check your system volume
- Verify speakers are working: `afplay /System/Library/Sounds/Ping.aiff`
- Check agent logs for TTS errors

### Agent Not Responding to Voice
- Speak clearly after the agent's greeting
- Check microphone permissions
- Look for "Transcribed:" messages in agent logs

### Slow Response Time
- First response is slowest (model loading)
- Consider using smaller models:
  - Whisper: Use "tiny" instead of "base"
  - Ollama: Use lighter models

### Audio Plays Too Slowly
- This should be fixed with automatic resampling
- If issues persist, check `src/local_tts.py` logs

## Testing Individual Components

- **Test Microphone**: `python test_client_with_mic.py`
- **Test TTS**: `python test_piper_direct.py`
- **Test Resampling**: `python test_resampling.py`
- **Test with Audio Playback**: `python test_with_audio_playback.py`

## Architecture

```
Your Voice → Microphone → LiveKit → Agent
                                      ↓
                                   Whisper STT
                                      ↓
                                   Ollama LLM
                                      ↓
                                   Piper TTS
                                      ↓
Speaker ← LiveKit ← Audio Frame ← Agent
```

All processing happens locally on your machine!