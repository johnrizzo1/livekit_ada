# Testing Your Local LiveKit Agent

## Prerequisites Check

1. **LiveKit Server** must be running at `ws://livekit.warthog-trout.ts.net:7880`
2. **Local Agent** should be running (you saw it register successfully)
3. **Whisper STT** is loaded and ready ✅
4. **Piper TTS** is installed and configured ✅

## Quick Test Methods

### Method 1: Web Browser Test (Easiest)

1. Run this command to get a test URL:
   ```bash
   python test_room_join.py
   ```

2. Copy the generated link that looks like:
   ```
   https://meet.livekit.io/?url=https://...&token=...
   ```

3. Open it in your web browser
4. Allow microphone access when prompted
5. Start speaking - the agent should respond!

### Method 2: Command Line Test

1. In Terminal 1 (keep your agent running):
   ```bash
   python -m src.agent_local start
   ```

2. In Terminal 2, run the simple test:
   ```bash
   python test_agent_simple.py
   ```

This will:
- Create a test room
- Wait for the agent to join
- Show you if the agent is responding

### Method 3: Python Client Test

Run the test client that simulates a participant:
```bash
python test_agent_client.py
```

This creates a room and waits for the agent to join and respond.

## What to Expect

When working correctly, you should see:

1. **Agent joins the room** - Look for "participant_connected" with agent identity
2. **Agent speaks greeting** - The agent should say hello when someone joins
3. **Agent responds to speech** - When you speak, agent transcribes and responds

## Troubleshooting

### Agent Not Joining Rooms

Check the agent terminal for errors:
- Authentication errors (401) - Wrong API keys
- Connection errors - LiveKit server not reachable
- Model loading errors - Missing Whisper/Piper files

### No Audio Response

1. Check if Piper is working:
   ```bash
   echo "Test" | devenv shell -- piper --model models/en_US-amy-low.onnx --output_file test.wav
   ```

2. Check if Ollama is running (for LLM):
   ```bash
   curl http://localhost:11434/api/tags
   ```
   
   If not, start it:
   ```bash
   ollama serve
   ```

### Agent Not Understanding Speech

Check Whisper is loaded - you should see in agent logs:
```
Whisper model loaded successfully
```

## Current Status

Based on our setup:
- ✅ LiveKit connection working
- ✅ Authentication working
- ✅ Whisper STT ready
- ✅ Piper TTS configured
- ⚠️  Ollama LLM - needs to be running separately

## Quick Commands Reference

```bash
# Test auth
python test_jwt_auth.py

# Get room join URL
python test_room_join.py

# Test Piper TTS
echo "Hello world" | devenv shell -- piper --model models/en_US-amy-low.onnx --output_file test.wav

# Start Ollama (in separate terminal)
ollama serve
ollama pull llama3.2:3b
```