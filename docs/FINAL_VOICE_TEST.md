# Final Voice Test Instructions

The issue is that the LiveKit server isn't automatically dispatching agents to rooms. Here's the working solution:

## Method 1: Start Modified Agent (Recommended)

**Terminal 1 - Start the auto-join agent:**
```bash
python agent_auto_join.py start
```

This agent will automatically join ANY room that's created.

**Terminal 2 - Run voice test:**
```bash
devenv shell -- python test_working_voice.py
```

## Method 2: Manual Room Connection

**Terminal 1 - Create room:**
```bash
devenv shell -- python simple_voice_test.py
```

**Terminal 2 - Manually connect agent:**
```bash
devenv shell -- python -m src.agent_local dev --room "voice-manual-test"
```

## What Should Happen

1. The agent will join the room
2. You'll see "🤖 Agent is here!" in the test client
3. The agent will greet you with audio through your speakers
4. You can then speak and have a conversation

## Troubleshooting

If it's still not working:

1. **Check Ollama is running:**
   ```bash
   curl http://localhost:11434/api/tags
   ```

2. **Check LiveKit server:**
   ```bash
   telnet 100.67.214.48 7880
   ```

3. **Check audio devices:**
   ```bash
   # List audio devices
   python -c "import pyaudio; p=pyaudio.PyAudio(); print([p.get_device_info_by_index(i)['name'] for i in range(p.get_device_count())])"
   ```

4. **Run with debug logging:**
   ```bash
   LOG_LEVEL=DEBUG python agent_auto_join.py start
   ```

## Direct Test

If you just want to test the audio is working, run:
```bash
devenv shell -- python test_resampling.py
```

This will generate and play TTS audio directly without needing the full agent setup.