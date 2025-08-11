# LiveKit Agent Room Joining

## The Issue

The LiveKit agent doesn't automatically join rooms when started with the `start` command. Instead, it operates in worker mode, waiting for job requests from LiveKit.

## How LiveKit Agents Work

1. **Worker Mode (`start`)**: The agent registers as a worker with LiveKit and waits for job assignments. LiveKit will assign the agent to rooms based on room configuration and agent availability.

2. **Direct Connect Mode (`connect`)**: The agent directly connects to a specific room. This is useful for testing and development.

3. **Development Mode (`dev`)**: Similar to worker mode but with hot-reload capabilities.

## Solutions

### Option 1: Direct Connection (Recommended for Testing)

Use the `connect` command to directly join a specific room:

```bash
python -m src.agent_local connect --room "test-agent-room"
```

Or use the provided script:
```bash
./test_agent_connect.sh
```

### Option 2: Configure Room for Agent Assignment

When creating a room via LiveKit API, you can specify that it requires an agent. The worker will then be automatically assigned to join the room.

### Option 3: Use Development Mode

Start the agent in dev mode and it will handle incoming connections:

```bash
python -m src.agent_local dev
```

## Testing Workflow

1. Start the agent in connect mode targeting your test room:
   ```bash
   ./test_agent_connect.sh
   ```

2. In another terminal, run your test client:
   ```bash
   python test_agent_client.py
   ```

3. The agent should now appear as a participant in the room and respond to audio input.

## Room Name Configuration

- The test client uses room name: `test-agent-room`
- When using `connect` mode, specify the same room name
- When using worker mode, ensure your room creation includes agent requirements

## Troubleshooting

1. **Agent not joining**: Make sure you're using `connect` mode with the correct room name
2. **No audio response**: Check that Ollama is running (`ollama serve`)
3. **Connection issues**: Verify LIVEKIT_URL, API_KEY, and API_SECRET in .env