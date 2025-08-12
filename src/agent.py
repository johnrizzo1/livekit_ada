#!/usr/bin/env python3
"""Agent with comprehensive status indicators - fixed version"""
import asyncio
import logging
import sys
from pathlib import Path
from livekit import api, rtc, agents
import os
from dotenv import load_dotenv
import numpy as np
import time
from datetime import datetime
import queue

from .local_whisper_stt import LocalWhisperSTT
from .local_piper_tts import LocalPiperTTS
from .status_indicator import StatusIndicator
from .conversation_agent import ConversationAgent
from livekit.plugins import openai

load_dotenv()

# Logger will be configured by main CLI
logger = logging.getLogger(__name__)

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
        
        # Thresholds - more sensitive to actual speech
        SPEECH_THRESHOLD = 500  # Increased to avoid noise triggering
        MIN_SPEECH_FRAMES = 10  # 0.2 seconds - shorter to catch quick speech
        MAX_SILENCE_FRAMES = 30  # 0.6 seconds - shorter pause detection
        
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
                
                # Log periodically with more detail
                if frame_count % 100 == 0:  # Every 2 seconds
                    logger.info(f"Frame {frame_count}: RMS={rms}, Speech={agent.speech_count}, "
                              f"Silence={agent.silence_count}, Recording={agent.is_recording}, "
                              f"AgentSpeaking={agent.is_agent_speaking}")
                
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
                            
                            if audio_to_process is not None and len(audio_to_process) > 3200:
                                logger.info(f"Processing audio: {len(audio_to_process)} samples")
                                # Transcribe
                                text = await agent.transcribe(audio_to_process, detected_sample_rate)
                                
                                if text and len(text) > 2:
                                    logger.info(f"STT SUCCESS: '{text}' - proceeding to LLM")
                                    # Check if in dictation mode
                                    if agent.is_dictating:
                                        # Check for dictation commands
                                        command, param = agent.detect_dictation_commands(text)
                                        
                                        if command == "save_dictation":
                                            success, result = agent.save_dictation(param)
                                            if success:
                                                response = f"Dictation saved to {result}"
                                            else:
                                                response = f"Failed to save dictation: {result}"
                                        elif command == "cancel_dictation":
                                            success, result = agent.cancel_dictation()
                                            response = result
                                        else:
                                            # Add to dictation
                                            agent.add_to_dictation(text)
                                            continue  # Don't generate response, just continue listening
                                    else:
                                        # Check for start dictation command
                                        command, param = agent.detect_dictation_commands(text)
                                        
                                        if command == "start_dictation":
                                            agent.start_dictation()
                                            response = "Starting dictation. Please begin speaking. Say 'Ada, save dictation as filename' when finished."
                                        else:
                                            # Normal conversation mode
                                            logger.info(f"Sending to LLM: '{text}'")
                                            response = await agent.generate_response(text)
                                            logger.info(f"LLM response received: '{response}'")
                                    
                                    if response:
                                        # Speak response - Set speaking flag EARLY
                                        agent.is_agent_speaking = True
                                        status.set_speaking(True)
                                        logger.info("Agent started speaking - blocking audio processing")
                                        
                                        try:
                                            tts_result = await agent.tts.synthesize(response)
                                            await audio_queue.put(tts_result.frame)
                                            
                                            # Calculate actual audio duration with more accurate timing
                                            audio_duration = len(tts_result.frame.data) / (48000 * 2)  # 48kHz, 16-bit
                                            buffer_time = max(1.0, audio_duration * 1.2)  # Reduced buffer: 1 second minimum or 20% extra
                                            
                                            logger.info(f"Audio duration: {audio_duration:.2f}s, waiting {buffer_time:.2f}s for playback + echo clearance")
                                            await asyncio.sleep(buffer_time)
                                            
                                        except Exception as e:
                                            logger.error(f"TTS error: {e}")
                                            # Even on error, wait a bit to prevent immediate processing
                                            await asyncio.sleep(1.0)
                                        finally:
                                            # Reduced extra delay to prevent long blocking
                                            await asyncio.sleep(0.5)  # Reduced from 1.0 to 0.5 seconds
                                            agent.is_agent_speaking = False
                                            status.set_speaking(False)
                                            logger.info("Agent finished speaking - resuming audio processing")
    
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
                
    @room.on("data_received")
    def on_data_received(data: rtc.DataPacket):
        """Handle incoming text messages from clients"""
        try:
            message = data.data.decode('utf-8')
            participant_identity = data.participant.identity if data.participant else "unknown"
            
            logger.info(f"Received text message from {participant_identity}: {message}")
            print(f"\n💬 Text from {participant_identity}: {message}")
            
            # Process the text message through the LLM pipeline
            async def process_text_message():
                try:
                    if message.strip():
                        # Check for dictation commands
                        if agent.is_dictating:
                            command, param = agent.detect_dictation_commands(message)
                            
                            if command == "save_dictation":
                                success, result = agent.save_dictation(param)
                                if success:
                                    response = f"Dictation saved to {result}"
                                else:
                                    response = f"Failed to save dictation: {result}"
                            elif command == "cancel_dictation":
                                success, result = agent.cancel_dictation()
                                response = result
                            else:
                                # Add to dictation
                                agent.add_to_dictation(message)
                                return  # Don't generate response
                        else:
                            # Check for start dictation command
                            command, param = agent.detect_dictation_commands(message)
                            
                            if command == "start_dictation":
                                agent.start_dictation()
                                response = "Starting dictation. Please begin speaking. Say 'Ada, save dictation as filename' when finished."
                            else:
                                # Normal conversation mode - process through LLM
                                response = await agent.generate_response(message)
                        
                        if response:
                            # Speak the response
                            agent.is_agent_speaking = True
                            status.set_speaking(True)
                            logger.info("Agent started speaking (text response)")
                            
                            try:
                                tts_result = await agent.tts.synthesize(response)
                                await audio_queue.put(tts_result.frame)
                                
                                # Calculate timing
                                audio_duration = len(tts_result.frame.data) / (48000 * 2)
                                buffer_time = max(2.0, audio_duration * 2.0)
                                
                                logger.info(f"Text response audio duration: {audio_duration:.2f}s, waiting {buffer_time:.2f}s")
                                await asyncio.sleep(buffer_time)
                                
                            except Exception as e:
                                logger.error(f"TTS error for text response: {e}")
                                await asyncio.sleep(1.0)
                            finally:
                                await asyncio.sleep(1.0)  # Extra buffer
                                agent.is_agent_speaking = False
                                status.set_speaking(False)
                                logger.info("Agent finished speaking (text response)")
                                
                except Exception as e:
                    logger.error(f"Error processing text message: {e}")
            
            # Run the text processing asynchronously
            asyncio.create_task(process_text_message())
            
        except Exception as e:
            logger.error(f"Error handling data message: {e}")
    
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


async def entrypoint(ctx: agents.JobContext):
    """LiveKit agent entrypoint function"""
    await ctx.connect(auto_subscribe=agents.AutoSubscribe.AUDIO_ONLY)
    
    # Create status indicator and agent
    status = StatusIndicator()
    agent = ConversationAgent(status)
    await agent.initialize()
    
    # Set up the conversation agent for the room
    # This is simplified - in practice you'd integrate with the room events
    logger.info(f"Agent connected to room: {ctx.room.name}")
    

if __name__ == "__main__":
    asyncio.run(main())