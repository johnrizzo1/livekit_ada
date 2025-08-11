# Active Context: Current State & Focus

## Current Project State

### What's Working ✅
- **Voice Pipeline**: Complete end-to-end voice conversation flow
- **Local Models**: Whisper STT, Piper TTS, and Ollama LLM all functional
- **LiveKit Integration**: Agent properly joins rooms and processes audio
- **Audio Processing**: 48kHz ↔ 16kHz ↔ 22kHz resampling chain works
- **Status Monitoring**: Real-time visual feedback system operational
- **Turn-taking**: VAD-based conversation flow with anti-echo protection

### Recent Achievements
- **ChatContext Fix**: Resolved LLM integration issues with new LiveKit API
- **Audio Timing**: Fixed slow playback with proper 48kHz output resampling
- **Logging Cleanup**: Comprehensive filter system eliminates noise in `run_ada.py`
- **Status Indicators**: Rich terminal-based monitoring for debugging

## Current Focus Areas

### Immediate Priority: Documentation Cleanup
The project has accumulated outdated documentation that doesn't reflect the current working implementation:

**Documentation Issues Identified:**
- `README.md`: References old file structure (`src/agent.py` doesn't exist)
- Multiple overlapping docs in `docs/` directory 
- Inconsistent setup instructions across different files
- Mix of cloud-based and local-first approaches in documentation

### Working Implementation vs Documentation Gap
**Reality (What Actually Works):**
- Main agent: `scripts/agent.py` (548 lines, fully functional)
- Entry point: `run_ada.py` with logging filters
- Local models: All working via proper integrations
- Audio pipeline: 48kHz LiveKit native with resampling

**Documentation Claims:**
- References `src/agent.py` (doesn't exist)
- Mentions old cloud service patterns
- Incomplete setup instructions
- Missing critical environment variables

## Key Patterns & Preferences Discovered

### Architecture Philosophy
- **Local-First**: Absolute commitment to privacy and offline operation
- **Real-Time**: Sub-second latency as core requirement
- **LiveKit Native**: Full integration with LiveKit's agent framework
- **Status Transparency**: Rich monitoring for debugging and user feedback

### Development Approach
- **Nix-Based**: Reproducible builds with devenv
- **Event-Driven**: AsyncIO with proper thread pool usage
- **Error Resilient**: Graceful degradation and comprehensive logging
- **User Experience**: Focus on natural conversation flow

### Code Quality Standards
- Clear separation of concerns (STT, TTS, LLM wrappers)
- Comprehensive status tracking and visual feedback
- Proper async/await patterns for I/O operations
- Thread pool execution for CPU-intensive tasks

## Recent Learnings & Project Insights

### Critical Implementation Details
1. **Audio Resampling**: Multiple format conversions require careful handling
2. **LiveKit API Changes**: ChatMessage format changed, requires list-based content
3. **Turn-Taking Logic**: Complex threshold-based system with pre-buffering
4. **Local Model Integration**: Each model has unique setup and execution patterns

### Performance Insights
- Whisper "base" model provides best latency/accuracy balance
- Piper TTS is significantly faster than alternatives
- Ollama integration via OpenAI API works seamlessly
- Status indicators need rate limiting to prevent terminal flooding

### Debugging Strategies  
- Log filtering essential due to LiveKit IPC pickle errors
- Visual status indicators crucial for understanding pipeline state
- Audio format validation prevents mysterious failures
- Real-time RMS monitoring helps diagnose audio issues

## Next Steps & Priorities

### High Priority
1. **Complete Memory Bank Setup** (current task)
2. **Remove Outdated Documentation** - Clean up `docs/` directory
3. **Update README.md** - Align with actual working implementation
4. **Validate Setup Instructions** - Ensure they work for new users

### Medium Priority  
- Create comprehensive troubleshooting guide
- Add automated testing for voice pipeline
- Document model selection and performance tradeoffs
- Create deployment guide for different environments

### Future Considerations
- Multi-language support (Whisper supports 99 languages)
- Voice cloning integration with Piper
- WebUI for non-technical users
- Performance optimization for lower-end hardware

## Context for Future Sessions

**When I return after memory reset, I need to know:**
- Ada is a **working** local voice agent, not a prototype
- Main implementation is in `scripts/agent.py`, not `src/agent.py`
- Documentation cleanup is the primary current need
- The voice pipeline architecture is stable and proven
- Focus should be on user experience and documentation quality

This project represents a complete, functional local voice AI system that prioritizes privacy and real-time performance.