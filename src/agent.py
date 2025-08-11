#!/usr/bin/env python3
"""Agent with comprehensive status indicators - fixed version"""
import asyncio
import logging
import sys
from pathlib import Path
from livekit import api, rtc
import os
from dotenv import load_dotenv
import numpy as np
import time
from datetime import datetime
import queue

# Add the parent directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.local_stt import LocalWhisperSTT
from src.local_tts import LocalPiperTTS
from livekit.plugins import openai

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class StatusIndicator:
    """Manages status display"""
    def __init__(self):
        self.current_status = ""
        self.audio_level = 0
        self.is_recording = False
        self.is_transcribing = False
        self.is_thinking = False
        self.is_speaking = False
        self.last_update = time.time()
        
    def update_audio_level(self, rms):
        """Update audio level indicator"""
        self.audio_level = rms
        self._print_status()
        
    def set_recording(self, recording):
        """Set recording status"""
        self.is_recording = recording
        self._print_status()
        
    def set_transcribing(self, transcribing):
        """Set transcribing status"""
        self.is_transcribing = transcribing
        self._print_status()
        
    def set_thinking(self, thinking):
        """Set LLM thinking status"""
        self.is_thinking = thinking
        self._print_status()
        
    def set_speaking(self, speaking):
        """Set TTS speaking status"""
        self.is_speaking = speaking
        self._print_status()
        
    def _print_status(self):
        """Print current status line"""
        # Rate limit updates
        if time.time() - self.last_update < 0.1:
            return
        self.last_update = time.time()
        
        # Build status line
        meter_level = min(10, int(self.audio_level / 1000))
        meter = "█" * meter_level + "░" * (10 - meter_level)
        
        # Audio level indicator
        if self.audio_level < 200:
            audio_status = "🔇"
        elif self.audio_level < 1000:
            audio_status = "🔉"
        else:
            audio_status = "🔊"
            
        # Pipeline status
        pipeline_parts = []
        if self.is_recording:
            pipeline_parts.append("🔴 RECORDING")
        if self.is_transcribing:
            pipeline_parts.append("🎙️ TRANSCRIBING")
        if self.is_thinking:
            pipeline_parts.append("🤔 THINKING")
        if self.is_speaking:
            pipeline_parts.append("📢 SPEAKING")
            
        if not pipeline_parts:
            pipeline_parts.append("⚪ LISTENING")
            
        pipeline_status = " → ".join(pipeline_parts)
        
        # Print status line
        status_line = f"\r{audio_status} [{meter}] {self.audio_level:4d} | {pipeline_status}"
        print(status_line + " " * 20, end="", flush=True)


class ConversationAgent:
    def __init__(self, status):
        self.status = status
        self.stt = None
        self.tts = None
        self.llm = None
        self.audio_buffer = []
        self.is_recording = False
        self.silence_count = 0
        self.speech_count = 0
        self.pre_buffer = []
        self.is_agent_speaking = False  # Track when agent is speaking
        self.messages = [
            {
                "role": "system",
                "content": (
                    "You are Ada, a helpful AI assistant. "
                    "Keep responses brief and conversational. "
                    "Limit responses to 2-3 sentences maximum."
                )
            }
        ]
        
    async def initialize(self):
        """Initialize all components"""
        print("\n🔧 Initializing components...")
        
        # STT
        print("  • Loading Whisper STT...")
        self.stt = LocalWhisperSTT(
            model_size=os.getenv("WHISPER_MODEL", "base"),
            device="auto",
            compute_type="int8",
            language="en",
        )
        
        # TTS
        print("  • Loading Piper TTS...")
        self.tts = LocalPiperTTS(
            model_path=os.getenv("PIPER_MODEL_PATH"),
            config_path=os.getenv("PIPER_CONFIG_PATH"),
            sample_rate=48000,
            num_channels=1,
        )
        
        # LLM
        print("  • Loading Ollama LLM...")
        self.llm = openai.LLM(
            model=os.getenv("OLLAMA_MODEL", "llama3.2:3b"),
            base_url="http://localhost:11434/v1",
            api_key="ollama",
        )
        
        print("✅ All components initialized\n")
        
    def start_recording(self):
        """Start recording audio"""
        self.is_recording = True
        self.audio_buffer = []
        self.status.set_recording(True)
        logger.info("Started recording")
        
    def stop_recording(self, sample_rate=16000):
        """Stop recording and return audio"""
        self.is_recording = False
        self.status.set_recording(False)
        
        if self.audio_buffer:
            # Combine all audio
            audio = np.concatenate(self.audio_buffer)
            duration = len(audio) / sample_rate
            # Check audio statistics
            max_val = np.max(np.abs(audio))
            mean_val = np.mean(np.abs(audio))
            logger.info(f"Stopped recording - {duration:.1f} seconds, {len(audio)} samples at {sample_rate}Hz, max: {max_val}, mean: {mean_val:.1f}")
            return audio
        return None
        
    def add_audio(self, audio_data):
        """Add audio to buffer if recording"""
        if self.is_recording:
            self.audio_buffer.append(audio_data)
            
    async def transcribe(self, audio_data, sample_rate=48000):
        """Transcribe audio using Whisper"""
        self.status.set_transcribing(True)
        
        try:
            # Convert to float32 for Whisper
            audio_float = audio_data.astype(np.float32) / 32768.0
            
            # Resample to 16kHz if needed (Whisper expects 16kHz)
            if sample_rate != 16000:
                import scipy.signal
                num_samples = int(len(audio_float) * 16000 / sample_rate)
                audio_float = scipy.signal.resample(audio_float, num_samples)
                logger.info(f"Resampled audio from {sample_rate}Hz to 16000Hz for Whisper")
            
            # Use the Whisper model directly
            loop = asyncio.get_event_loop()
            segments, info = await loop.run_in_executor(
                None,
                self._transcribe_sync,
                audio_float
            )
            
            if segments:
                text = " ".join(segment.text.strip() for segment in segments)
                print(f"\n💬 USER: {text}")
                return text
            else:
                logger.warning("No transcription result")
                return None
                
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            import traceback
            traceback.print_exc()
            return None
        finally:
            self.status.set_transcribing(False)
            
    def _transcribe_sync(self, audio_data):
        """Synchronous transcription for executor"""
        segments, info = self.stt._model.transcribe(
            audio_data,
            beam_size=5,
            language="en",
            vad_filter=False,  # Disable VAD to see raw transcription
        )
        return list(segments), info
            
    async def generate_response(self, user_text):
        """Generate AI response"""
        self.status.set_thinking(True)
        
        try:
            self.messages.append({"role": "user", "content": user_text})
            
            # Import LLM types
            from livekit.agents import llm as agent_llm
            
            # Create chat messages with list format (required by the API)
            chat_messages = []
            for msg in self.messages:
                # Content must be a list of strings
                chat_msg = agent_llm.ChatMessage(
                    role=msg["role"],
                    content=[msg["content"]]
                )
                chat_messages.append(chat_msg)
            
            # Create chat context with messages - pass messages in constructor
            chat_ctx = agent_llm.ChatContext(chat_messages)
            
            # Debug logging
            logger.info(f"Chat context has {len(chat_ctx.items)} messages")
            for i, msg in enumerate(chat_ctx.items):
                if hasattr(msg, 'role') and hasattr(msg, 'content'):
                    logger.info(f"Message {i}: role={msg.role}, content={msg.content}")
            
            # Get response from LLM
            response_stream = self.llm.chat(chat_ctx=chat_ctx)
            
            response_text = ""
            async for chunk in response_stream:
                # Handle LiveKit ChatChunk format (different from OpenAI)
                if hasattr(chunk, 'content') and chunk.content:
                    response_text += chunk.content
                elif hasattr(chunk, 'choices') and chunk.choices and len(chunk.choices) > 0:
                    # Fallback for OpenAI-style format
                    choice = chunk.choices[0]
                    if hasattr(choice, 'delta') and choice.delta:
                        if hasattr(choice.delta, 'content') and choice.delta.content:
                            if isinstance(choice.delta.content, str):
                                response_text += choice.delta.content
                            elif isinstance(choice.delta.content, list):
                                for content_item in choice.delta.content:
                                    if isinstance(content_item, str):
                                        response_text += content_item
                                    elif hasattr(content_item, 'text') and content_item.text:
                                        response_text += content_item.text
            
            if response_text:
                self.messages.append({"role": "assistant", "content": response_text})
                print(f"🤖 ADA: {response_text}")
                return response_text
                
        except Exception as e:
            logger.error(f"LLM error: {e}")
            import traceback
            traceback.print_exc()
            return "I'm sorry, I had trouble processing that."
        finally:
            self.status.set_thinking(False)


async def run_agent(room_name="test-room"):
    """Run the conversational agent"""
    print("\n🚀 Starting Ada - Conversational AI Agent")
    print("="*60)
    
    # Create status indicator
    status = StatusIndicator()
    
    # Create agent
    agent = ConversationAgent(status)
    await agent.initialize()
    
    # Get connection details
    url = os.getenv("LIVEKIT_URL", "ws://localhost:7880")
    api_key = os.getenv("LIVEKIT_API_KEY", "devkey")
    api_secret = os.getenv("LIVEKIT_API_SECRET", "secret")
    
    # Create token
    token = api.AccessToken(api_key, api_secret)
    token.with_identity("ada-agent").with_name("Ada")
    token.with_grants(api.VideoGrants(
        room_join=True,
        room=room_name,
        can_publish=True,
        can_subscribe=True,
        agent=True,
    ))
    
    # Create room
    room = rtc.Room()
    
    # Create audio output queue
    audio_queue = asyncio.Queue()
    
    async def audio_sender(audio_source):
        """Handle sending audio to avoid conflicts"""
        while True:
            audio_frame = await audio_queue.get()
            if audio_frame is None:
                break
            try:
                await audio_source.capture_frame(audio_frame)
            except Exception as e:
                logger.error(f"Error sending audio: {e}")
    
    # Process audio function
    async def process_audio(track, participant):
        """Process incoming audio"""
        print(f"\n🎤 Processing audio from {participant.identity}")
        logger.info(f"Started processing audio from {participant.identity}")
        
        audio_stream = rtc.AudioStream(track)
        
        # Thresholds
        SPEECH_THRESHOLD = 200
        MIN_SPEECH_FRAMES = 20  # 0.4 seconds
        MAX_SILENCE_FRAMES = 40  # 0.8 seconds
        
        frame_count = 0
        
        first_frame = True
        detected_sample_rate = 16000
        
        async for event in audio_stream:
            if isinstance(event, rtc.AudioFrameEvent):
                frame_count += 1
                
                # Log first frame info
                if first_frame:
                    first_frame = False
                    detected_sample_rate = event.frame.sample_rate
                    logger.info(f"Audio format: {event.frame.sample_rate}Hz, {event.frame.num_channels}ch, {event.frame.samples_per_channel} samples/channel")
                
                # Get audio
                audio_data = np.frombuffer(event.frame.data, dtype=np.int16)
                rms = int(np.sqrt(np.mean(audio_data.astype(float)**2)))
                
                # Update status display
                status.update_audio_level(rms)
                
                # Log periodically
                if frame_count % 100 == 0:  # Every 2 seconds
                    logger.info(f"Audio stats - Frame {frame_count}, RMS: {rms}, Speech count: {agent.speech_count}, Recording: {agent.is_recording}, Agent speaking: {agent.is_agent_speaking}")
                
                # Skip processing if agent is speaking
                if agent.is_agent_speaking:
                    # Reset counters while agent speaks
                    agent.speech_count = 0
                    agent.silence_count = 0
                    if agent.is_recording:
                        agent.stop_recording(detected_sample_rate)
                        logger.info("Stopped recording - agent started speaking")
                    continue
                
                # Always add to a circular buffer for pre-recording
                agent.pre_buffer.append(audio_data)
                if len(agent.pre_buffer) > 50:  # Keep last 1 second
                    agent.pre_buffer.pop(0)
                
                # Detect speech/silence
                if rms > SPEECH_THRESHOLD:
                    agent.speech_count += 1
                    agent.silence_count = 0
                    
                    # Start recording after consistent speech
                    if agent.speech_count >= MIN_SPEECH_FRAMES and not agent.is_recording:
                        agent.start_recording()
                        # Add pre-buffer to recording
                        for pre_audio in agent.pre_buffer:
                            agent.add_audio(pre_audio)
                    
                    if agent.is_recording:
                        agent.add_audio(audio_data)
                    
                else:  # Silence
                    agent.silence_count += 1
                    
                    if agent.is_recording:
                        agent.add_audio(audio_data)
                        
                        # Stop after enough silence
                        if agent.silence_count >= MAX_SILENCE_FRAMES:
                            audio_to_process = agent.stop_recording(detected_sample_rate)
                            agent.speech_count = 0
                            
                            if audio_to_process is not None and len(audio_to_process) > 8000:
                                # Transcribe
                                text = await agent.transcribe(audio_to_process, detected_sample_rate)
                                
                                if text and len(text) > 2:
                                    # Generate response
                                    response = await agent.generate_response(text)
                                    
                                    if response:
                                        # Speak response
                                        agent.is_agent_speaking = True
                                        status.set_speaking(True)
                                        try:
                                            tts_result = await agent.tts.synthesize(response)
                                            await audio_queue.put(tts_result.frame)
                                            # Wait a bit for audio to finish playing
                                            await asyncio.sleep(len(tts_result.frame.data) / (48000 * 2 * 1.2))  # duration + 20% buffer
                                        except Exception as e:
                                            logger.error(f"TTS error: {e}")
                                        finally:
                                            agent.is_agent_speaking = False
                                            status.set_speaking(False)
    
    # Event handlers
    @room.on("connected")
    def on_connected():
        print(f"✅ Connected to room: {room_name}")
        print(f"🔗 Room SID: {room.sid}")
    
    @room.on("participant_connected")
    def on_participant_connected(participant):
        print(f"\n👤 {participant.identity} joined the room")
        # Check for existing tracks
        for publication in participant.track_publications.values():
            if publication.kind == rtc.TrackKind.KIND_AUDIO and publication.track:
                print(f"   🎤 Found existing audio track, processing...")
                asyncio.create_task(process_audio(publication.track, participant))
    
    @room.on("participant_disconnected")
    def on_participant_disconnected(participant):
        print(f"\n👋 {participant.identity} left the room")
    
    @room.on("track_published")
    def on_track_published(publication, participant):
        kind_name = "audio" if publication.kind == rtc.TrackKind.KIND_AUDIO else "video" if publication.kind == rtc.TrackKind.KIND_VIDEO else str(publication.kind)
        print(f"\n📡 Track published by {participant.identity}: {kind_name}")
        print(f"   Track name: {publication.name}")
        print(f"   Track SID: {publication.sid}")
        print(f"   Subscribed: {publication.subscribed}")
        
        # Force subscription if it's audio and not already subscribed
        if publication.kind == rtc.TrackKind.KIND_AUDIO and not publication.subscribed:
            print("   ⚠️  Audio track not auto-subscribed, attempting to subscribe...")
            publication.set_subscribed(True)
    
    @room.on("track_subscribed")
    def on_track_subscribed(track, publication, participant):
        if track.kind == rtc.TrackKind.KIND_AUDIO:
            print(f"\n🎧 Successfully subscribed to audio from {participant.identity}")
            asyncio.create_task(process_audio(track, participant))
    
    # Connect with auto-subscribe enabled
    print(f"\n📡 Connecting to {url}...")
    await room.connect(url, token.to_jwt(), options=rtc.RoomOptions(
        auto_subscribe=True,
        dynacast=True,
    ))
    
    # Create audio output
    audio_source = rtc.AudioSource(48000, 1)
    audio_track = rtc.LocalAudioTrack.create_audio_track("ada-voice", audio_source)
    await room.local_participant.publish_track(audio_track)
    print("🔊 Audio track published")
    
    # Start audio sender task
    audio_sender_task = asyncio.create_task(audio_sender(audio_source))
    
    # Send greeting
    print("\n🎤 Sending greeting...")
    greeting = "Hello! I'm Ada. How can I help you today?"
    agent.is_agent_speaking = True
    status.set_speaking(True)
    try:
        result = await agent.tts.synthesize(greeting)
        await audio_queue.put(result.frame)
        print(f"🤖 ADA: {greeting}")
        # Wait for greeting to finish
        await asyncio.sleep(len(result.frame.data) / (48000 * 2 * 1.2))
    except Exception as e:
        logger.error(f"TTS error: {e}")
    finally:
        agent.is_agent_speaking = False
        status.set_speaking(False)
    
    print("\n" + "="*60)
    print("PIPELINE STATUS:")
    print("="*60)
    
    print("\n🎯 Agent ready! Waiting for participants...")
    
    # Keep running
    try:
        while room.connection_state == rtc.ConnectionState.CONN_CONNECTED:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n\nShutting down...")
    finally:
        await room.disconnect()


async def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("room", nargs="?", default="test-room")
    args = parser.parse_args()
    
    await run_agent(args.room)


if __name__ == "__main__":
    asyncio.run(main())