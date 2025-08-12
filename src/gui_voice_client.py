#!/usr/bin/env python3
"""Clean Voice Client for GUI Interface"""
import asyncio
import logging
from livekit import api, rtc
import pyaudio
import numpy as np
from dotenv import load_dotenv
import os
import threading
import queue
import time

load_dotenv()

logger = logging.getLogger(__name__)


class CleanVoiceClient:
    """Voice client that doesn't print to stdout - designed for GUI interfaces"""
    
    def __init__(self, status_display, conversation_display=None):
        self.status = status_display
        self.conversation = conversation_display
        self.room = rtc.Room()
        self.audio = pyaudio.PyAudio()
        self.mic_stream = None
        self.speaker_stream = None
        self.audio_queue = queue.Queue()
        self.playback_thread = None
        
        # Setup room events
        self.setup_room_events()
        
        # Status tracking
        self.connected = False
        
    def setup_room_events(self):
        """Setup LiveKit room event handlers"""
        
        @self.room.on("connected")
        def on_connected():
            logger.info("Connected to room")
            self.connected = True
            if self.status:
                self.status.set_connection_status("📡 Connected")
            if self.conversation:
                self.conversation.add_system_message("✅ Voice connection established")
        
        @self.room.on("disconnected") 
        def on_disconnected():
            logger.info("Disconnected from room")
            self.connected = False
            if self.status:
                self.status.set_connection_status("📡 Disconnected")
            if self.conversation:
                self.conversation.add_system_message("❌ Voice connection lost")
        
        @self.room.on("participant_connected")
        def on_participant_connected(participant: rtc.RemoteParticipant):
            logger.info(f"Participant connected: {participant.identity}")
            if self.conversation:
                self.conversation.add_system_message(f"👤 {participant.identity} joined the room")
        
        @self.room.on("track_subscribed")
        def on_track_subscribed(track: rtc.Track, publication: rtc.TrackPublication, participant: rtc.RemoteParticipant):
            logger.info(f"Track subscribed: {track.kind} from {participant.identity}")
            if track.kind == rtc.TrackKind.KIND_AUDIO:
                if self.conversation:
                    self.conversation.add_system_message(f"🔊 Receiving audio from {participant.identity}")
                self.setup_audio_playback(track)
        
        @self.room.on("track_unsubscribed")
        def on_track_unsubscribed(track: rtc.Track, publication: rtc.TrackPublication, participant: rtc.RemoteParticipant):
            logger.info(f"Track unsubscribed: {track.kind} from {participant.identity}")
    
    def setup_audio_playback(self, track):
        """Setup audio playback from agent"""
        audio_stream = rtc.AudioStream(track)
        
        def playback_worker():
            """Worker thread for audio playback"""
            stream = None
            try:
                while True:
                    try:
                        audio_data, sample_rate, channels = self.audio_queue.get(timeout=0.1)
                        
                        # Create stream if needed
                        if stream is None:
                            logger.info(f"Creating speaker stream: {sample_rate}Hz, {channels}ch")
                            stream = self.audio.open(
                                format=pyaudio.paInt16,
                                channels=channels,
                                rate=sample_rate,
                                output=True,
                                frames_per_buffer=320
                            )
                        
                        # Update agent speaking status
                        if self.status:
                            rms = np.sqrt(np.mean(np.frombuffer(audio_data, dtype=np.int16).astype(float) ** 2))
                            self.status.set_agent_speaking(rms > 100)
                        
                        # Play audio
                        stream.write(audio_data)
                        
                    except queue.Empty:
                        continue
                    except Exception as e:
                        logger.error(f"Playback error: {e}")
                        continue
                        
            finally:
                if stream:
                    try:
                        stream.stop_stream()
                        stream.close()
                    except Exception:
                        pass  # Ignore close errors
        
        # Start playback thread
        self.playback_thread = threading.Thread(target=playback_worker, daemon=True)
        self.playback_thread.start()
        
        # Handle incoming audio frames
        async def audio_frame_received(frame: rtc.AudioFrame):
            audio_data = frame.data.tobytes()
            self.audio_queue.put((audio_data, frame.sample_rate, frame.num_channels))
        
        # Convert to audio stream and handle frames
        asyncio.create_task(self._handle_audio_stream(audio_stream))
    
    async def _handle_audio_stream(self, audio_stream):
        """Handle incoming audio stream"""
        frame_count = 0
        async for frame in audio_stream:
            frame_count += 1
            audio_data = frame.data.tobytes()
            self.audio_queue.put((audio_data, frame.sample_rate, frame.num_channels))
            
            # Log periodically
            if frame_count % 100 == 0:
                logger.info(f"Received {frame_count} audio frames, queue size: {self.audio_queue.qsize()}")
    
    async def connect(self, room_name: str):
        """Connect to LiveKit room"""
        url = os.getenv("LIVEKIT_URL", "ws://localhost:7880")
        token = os.getenv("LIVEKIT_TOKEN", "")
        
        if not token:
            # Generate a simple token for local development
            token = api.AccessToken() \
                .with_identity("user") \
                .with_name("Voice User") \
                .with_grants(api.VideoGrants(room_join=True, room=room_name)) \
                .to_jwt()
        
        if self.status:
            self.status.set_connection_status("📡 Connecting")
            
        await self.room.connect(url, token)
        
        # Setup microphone
        await self.setup_microphone()
        
        if self.conversation:
            self.conversation.add_system_message("🎤 Microphone ready")
            self.conversation.add_system_message("💬 Text input ready - type and press Enter")
    
    async def setup_microphone(self):
        """Setup microphone audio capture"""
        # Create audio source
        audio_source = rtc.AudioSource(24000, 1)
        
        # Create and publish audio track
        audio_track = rtc.LocalAudioTrack.create_audio_track("microphone", audio_source)
        await self.room.local_participant.publish_track(audio_track)
        
        # Setup microphone stream
        self.mic_stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=24000,
            input=True,
            frames_per_buffer=320
        )
        
        # Start microphone worker
        def mic_worker():
            frame = rtc.AudioFrame.create(24000, 1, 320)
            while self.connected:
                try:
                    audio_data = self.mic_stream.read(320, exception_on_overflow=False)
                    
                    # Copy audio data to frame
                    np.frombuffer(frame.data, dtype=np.int16)[:] = np.frombuffer(audio_data, dtype=np.int16)
                    
                    # Calculate RMS for status display
                    if self.status:
                        audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(float)
                        rms = np.sqrt(np.mean(audio_array ** 2))
                        self.status.update_mic_level(int(rms))
                    
                    # Capture audio
                    asyncio.run_coroutine_threadsafe(
                        audio_source.capture_frame(frame),
                        asyncio.get_event_loop()
                    )
                    
                except Exception as e:
                    logger.error(f"Microphone error: {e}")
                    break
        
        # Start microphone thread
        mic_thread = threading.Thread(target=mic_worker, daemon=True)
        mic_thread.start()
    
    async def send_text_message(self, message: str):
        """Send text message to agent via data channel"""
        if self.room and self.room.connection_state == rtc.ConnectionState.CONN_CONNECTED:
            try:
                data_packet = rtc.DataPacket(
                    data=message.encode('utf-8'),
                    kind=rtc.DataPacketKind.LOSSY,
                    destination=[participant.sid for participant in self.room.remote_participants.values()]
                )
                await self.room.local_participant.publish_data(data_packet)
                logger.info(f"📤 Sent text message: '{message}'")
                if self.conversation:
                    self.conversation.add_system_message(f"📤 Sent: {message}")
            except Exception as e:
                logger.error(f"Failed to send text message: {e}")
                if self.conversation:
                    self.conversation.add_system_message(f"❌ Failed to send message: {e}")
    
    async def disconnect(self):
        """Disconnect from room and cleanup"""
        self.connected = False
        
        if self.mic_stream:
            self.mic_stream.stop_stream()
            self.mic_stream.close()
            
        if self.speaker_stream:
            self.speaker_stream.stop_stream()
            self.speaker_stream.close()
            
        await self.room.disconnect()
        self.audio.terminate()
        
        if self.playback_thread:
            self.playback_thread.join(timeout=1)