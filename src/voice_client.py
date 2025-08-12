import os
import logging
import asyncio
import threading
import queue
import time
import uuid
import numpy as np
import pyaudio
from livekit import api, rtc
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class VoiceClient:
    """Voice client with status indicators"""
    
    def __init__(self, status, conversation_callback=None):
        self.status = status
        self.conversation_callback = conversation_callback
        self.room = rtc.Room()
        self.audio = pyaudio.PyAudio()
        self.mic_stream = None
        self.speaker_stream = None
        self.audio_queue = queue.Queue()
        self.playback_thread = None
        self.running = True
        
    async def send_text_message(self, message: str):
        """Send text message to agent via data channel"""
        try:
            if (self.room.connection_state ==
                rtc.ConnectionState.CONN_CONNECTED):
                data = message.encode('utf-8')
                await self.room.local_participant.publish_data(data)
                logger.info(f"Sent text message to agent: {message}")
            else:
                logger.warning("Cannot send message - not connected to room")
        except Exception as e:
            logger.error(f"Error sending text message: {e}")
        
    async def connect(self, room_name: str = "test-room"):
        """Connect to LiveKit room"""
        url = os.getenv("LIVEKIT_URL", "ws://localhost:7880")
        api_key = os.getenv("LIVEKIT_API_KEY", "devkey")
        api_secret = os.getenv("LIVEKIT_API_SECRET", "secret")
        
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        
        token = api.AccessToken(api_key, api_secret)
        token.with_identity(f"user-{unique_id}").with_name("User")
        token.with_grants(api.VideoGrants(
            room_join=True,
            room=room_name,
            can_publish=True,
            can_subscribe=True
        ))
        
        @self.room.on("connected")
        def on_connected():
            self.status.set_connection_status("✅ Connected")
            print(f"\n✅ Connected to room: {room_name}")
            print(f"🔗 Room SID: {self.room.sid}")
            print(f"🔗 Local participant: "
                  f"{self.room.local_participant.identity}")
            
            # List participants
            if self.room.remote_participants:
                print("\n📋 Participants in room:")
                for p in self.room.remote_participants.values():
                    print(f"  • {p.identity}")
                    if "agent" in p.identity.lower():
                        print("    🤖 (AI Agent detected)")
            else:
                print("\n⏳ Waiting for agent to join...")
            
        @self.room.on("participant_connected")
        def on_participant_connected(participant):
            print(f"\n👤 {participant.identity} joined")
            if "agent" in participant.identity.lower():
                print("🤖 AI Agent is now in the room!")
            
        @self.room.on("participant_disconnected")
        def on_participant_disconnected(participant):
            print(f"\n👋 {participant.identity} left")
            
        @self.room.on("track_subscribed")
        def on_track_subscribed(track, publication, participant):
            if track.kind == rtc.TrackKind.KIND_AUDIO:
                print(f"\n🔊 Receiving audio from {participant.identity}")
                asyncio.create_task(self.receive_audio(track))
        
        @self.room.on("data_received")
        def on_data_received(data):
            try:
                message = data.data.decode('utf-8')
                logger.info(f"Received data from {data.participant.identity}: {message}")
                
                # Check if this is an agent response and we have a callback
                if (self.conversation_callback and
                    data.participant and
                    "agent" in data.participant.identity.lower()):
                    self.conversation_callback("agent", message)
                    
                # Check if this is a user message (transcription)
                elif (self.conversation_callback and
                      data.participant and
                      data.participant.identity == self.room.local_participant.identity):
                    self.conversation_callback("user", message)
                    
            except Exception as e:
                logger.error(f"Error handling data: {e}")
        
        print(f"📡 Connecting to {url}...")
        self.status.set_connection_status("📡 Connecting...")
        
        await self.room.connect(url, token.to_jwt())
        
        # Log connection state after connect
        print(f"🔗 Connection state: {self.room.connection_state}")
        participant_sid = (self.room.local_participant.sid
                          if self.room.local_participant else 'None')
        print(f"🔗 Local participant SID: {participant_sid}")
        
        # Start playback thread
        self.start_playback_thread()
        
        # Start publishing microphone
        await self.publish_microphone()
        
    def start_playback_thread(self):
        """Start background thread for audio playback"""
        def playback_worker():
            logger.info("Starting audio playback thread")
            
            while self.running:
                try:
                    # Get audio from queue
                    audio_data, sample_rate, channels = (
                        self.audio_queue.get(timeout=0.1))
                    
                    self.status.set_agent_speaking(True)
                    
                    # Create/update speaker stream
                    if self.speaker_stream is None:
                        logger.info(f"Creating speaker stream: "
                                   f"{sample_rate}Hz, {channels}ch")
                        self.speaker_stream = self.audio.open(
                            format=pyaudio.paInt16,
                            channels=channels,
                            rate=sample_rate,
                            output=True,
                            frames_per_buffer=len(audio_data) // 2
                        )
                    
                    # Play audio
                    self.speaker_stream.write(audio_data)
                    
                    # Check audio level
                    audio_array = np.frombuffer(audio_data, dtype=np.int16)
                    rms = int(np.sqrt(np.mean(audio_array.astype(float)**2)))
                    logger.info(f"Played audio chunk: {len(audio_data)} bytes, "
                               f"{sample_rate}Hz, {channels}ch, RMS: {rms}")
                    
                except queue.Empty:
                    self.status.set_agent_speaking(False)
                    continue
                except Exception as e:
                    logger.error(f"Playback error: {e}")
                    if self.speaker_stream:
                        try:
                            self.speaker_stream.stop_stream()
                            self.speaker_stream.close()
                        except:
                            pass
                        self.speaker_stream = None
        
        self.playback_thread = threading.Thread(target=playback_worker,
                                               daemon=True)
        self.playback_thread.start()
        
    async def publish_microphone(self):
        """Publish microphone audio"""
        print("\n🎤 Starting microphone...")
        
        # Create audio source
        audio_source = rtc.AudioSource(16000, 1)
        audio_track = rtc.LocalAudioTrack.create_audio_track(
            "microphone", audio_source)
        
        await self.room.local_participant.publish_track(audio_track)
        print("📡 Publishing microphone audio")
        
        # Open mic stream
        self.mic_stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=320  # 20ms at 16kHz
        )
        
        print("\n" + "="*60)
        print("VOICE CHAT ACTIVE")
        print("="*60)
        print()
        
        frame_count = 0
        while self.room.connection_state == rtc.ConnectionState.CONN_CONNECTED:
            try:
                # Read from mic
                audio_data = self.mic_stream.read(
                    320, exception_on_overflow=False)
                
                # Create frame
                frame = rtc.AudioFrame.create(16000, 1, 320)
                np.frombuffer(frame.data, dtype=np.int16)[:] = (
                    np.frombuffer(audio_data, dtype=np.int16))
                
                # Send frame
                await audio_source.capture_frame(frame)
                
                # Update status
                frame_count += 1
                if frame_count % 5 == 0:  # Every 100ms
                    audio_array = np.frombuffer(
                        audio_data, dtype=np.int16).astype(float)
                    rms = int(np.sqrt(np.mean(audio_array**2)))
                    self.status.update_mic_level(rms)
                
            except Exception as e:
                logger.error(f"Microphone error: {e}")
                break
                
    async def receive_audio(self, track):
        """Receive and queue audio"""
        audio_stream = rtc.AudioStream(track)
        frame_count = 0
        
        async for event in audio_stream:
            if isinstance(event, rtc.AudioFrameEvent):
                frame = event.frame
                frame_count += 1
                if frame_count % 50 == 0:  # Log every 50 frames
                    logger.info(f"Received {frame_count} audio frames, "
                               f"queue size: {self.audio_queue.qsize()}")
                self.audio_queue.put((
                    bytes(frame.data),
                    frame.sample_rate,
                    frame.num_channels
                ))
                
    async def disconnect(self):
        """Disconnect from room"""
        self.running = False
        
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

