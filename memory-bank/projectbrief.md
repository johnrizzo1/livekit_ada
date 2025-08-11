# Project Brief: LiveKit Ada Voice Agent

## Core Mission
Build "Ada" - a fully local, offline voice AI agent using LiveKit for real-time voice conversations with complete privacy and low-latency local processing.

## Project Identity
- **Name**: Ada (LiveKit Voice Agent)  
- **Type**: Real-time conversational AI agent
- **Scope**: Local voice processing system
- **Architecture**: Event-driven voice pipeline

## Core Requirements

### Voice Pipeline
- **STT**: Local Whisper (faster-whisper) for speech recognition
- **LLM**: Local Ollama integration via OpenAI-compatible API  
- **TTS**: Local Piper TTS for speech synthesis
- **VAD**: Silero Voice Activity Detection
- **Audio**: 48kHz LiveKit audio with proper resampling

### System Properties
- **Local-first**: No cloud dependencies for core functionality
- **Real-time**: Low-latency voice conversations
- **LiveKit native**: Full integration with LiveKit's agent framework
- **Privacy**: Complete offline operation
- **Scalable**: Agent-per-room architecture

### Technical Constraints
- Must work with LiveKit server (local or remote)
- Audio format compatibility (16kHz input, 48kHz output)
- Cross-platform support via Nix flakes
- Event-driven status indicators and monitoring

## Success Criteria
1. Sub-second voice-to-voice latency
2. Natural conversation flow with proper turn-taking
3. Reliable audio quality and timing
4. Robust error handling and recovery
5. Clear monitoring and debugging capabilities

## Current Status
- Core voice pipeline: **WORKING**
- LiveKit integration: **WORKING** 
- Local STT/TTS: **WORKING**
- LLM integration: **WORKING**
- Documentation: **NEEDS UPDATE**

This project represents a complete voice AI system built on LiveKit's agent framework with full local processing capabilities.