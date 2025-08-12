import os
import logging
import asyncio
import numpy as np
from pathlib import Path
from livekit.plugins import openai
from .local_whisper_stt import LocalWhisperSTT
from .local_piper_tts import LocalPiperTTS

logger = logging.getLogger(__name__)


class ConversationAgent:
    def __init__(self, status, conversation_callback=None):
        self.status = status
        self.conversation_callback = conversation_callback
        self.stt = None
        self.tts = None
        self.llm = None
        self.audio_buffer = []
        self.is_recording = False
        self.silence_count = 0
        self.speech_count = 0
        self.pre_buffer = []
        self.is_agent_speaking = False  # Track when agent is speaking
        
        # Dictation state
        self.is_dictating = False
        self.dictation_text = ""
        self.dictation_filename = None
        
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
    
    def detect_dictation_commands(self, text):
        """Detect dictation commands in user text"""
        text_lower = text.lower().strip()
        
        # Start dictation commands
        start_phrases = [
            "ada, start dictation",
            "ada, take dictation",
            "ada, begin dictation",
            "start dictation",
            "take dictation"
        ]
        
        for phrase in start_phrases:
            if phrase in text_lower:
                return "start_dictation", None
        
        # Save dictation commands - extract filename
        if "ada, save dictation" in text_lower or "save dictation" in text_lower:
            # Try to extract filename
            parts = text_lower.split("as ")
            if len(parts) > 1:
                filename = parts[-1].strip()
                # Clean up filename
                filename = filename.replace(".", "").replace(",", "")
                if not filename.endswith(".txt"):
                    filename += ".txt"
                return "save_dictation", filename
            else:
                return "save_dictation", "dictation.txt"
        
        # Cancel dictation commands
        cancel_phrases = [
            "ada, cancel dictation",
            "ada, stop dictation",
            "cancel dictation",
            "stop dictation"
        ]
        
        for phrase in cancel_phrases:
            if phrase in text_lower:
                return "cancel_dictation", None
                
        return None, None
    
    def start_dictation(self):
        """Start dictation mode"""
        self.is_dictating = True
        self.dictation_text = ""
        self.status.set_dictating(True)
        logger.info("Started dictation mode")
        
    def add_to_dictation(self, text):
        """Add text to current dictation"""
        if self.is_dictating:
            if self.dictation_text:
                self.dictation_text += " " + text
            else:
                self.dictation_text = text
            logger.info(f"Added to dictation: {text}")
    
    def save_dictation(self, filename="dictation.txt"):
        """Save dictation to file and end dictation mode"""
        if not self.is_dictating:
            return False, "Not in dictation mode"
            
        if not self.dictation_text.strip():
            return False, "No dictation content to save"
        
        try:
            # Create dictations directory if it doesn't exist
            dictations_dir = Path("dictations")
            dictations_dir.mkdir(exist_ok=True)
            
            # Save to file
            file_path = dictations_dir / filename
            with open(file_path, 'w') as f:
                f.write(self.dictation_text.strip())
            
            # End dictation mode
            self.is_dictating = False
            self.status.set_dictating(False)
            
            logger.info(f"Saved dictation to {file_path}")
            return True, str(file_path)
            
        except Exception as e:
            logger.error(f"Error saving dictation: {e}")
            return False, f"Error saving file: {e}"
    
    def cancel_dictation(self):
        """Cancel dictation mode without saving"""
        if not self.is_dictating:
            return False, "Not in dictation mode"
            
        self.is_dictating = False
        self.dictation_text = ""
        self.status.set_dictating(False)
        logger.info("Cancelled dictation mode")
        return True, "Dictation cancelled"
        
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
                logger.info(f"User said: {text}")
                if self.conversation_callback:
                    self.conversation_callback("user", text)
                else:
                    print(f"\n💬 USER: {text}")
                return text
            else:
                logger.warning("No transcription result - empty segments")
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
                # Debug the chunk format
                logger.debug(f"LLM chunk received: {type(chunk)} - {chunk}")
                
                # Handle LiveKit ChatChunk format with delta - this is what we're getting!
                if hasattr(chunk, 'delta') and chunk.delta and hasattr(chunk.delta, 'content') and chunk.delta.content:
                    content = chunk.delta.content
                    logger.debug(f"Using chunk.delta.content: {content}")
                    response_text += content
                # Handle LiveKit ChatChunk format
                elif hasattr(chunk, 'content') and chunk.content:
                    logger.debug(f"Using chunk.content: {chunk.content}")
                    response_text += chunk.content
                # Handle OpenAI-style streaming format (used by Ollama)
                elif hasattr(chunk, 'choices') and chunk.choices and len(chunk.choices) > 0:
                    choice = chunk.choices[0]
                    if hasattr(choice, 'delta') and choice.delta:
                        if hasattr(choice.delta, 'content') and choice.delta.content:
                            content = choice.delta.content
                            logger.debug(f"Using choice.delta.content: {content}")
                            if isinstance(content, str):
                                response_text += content
                            elif isinstance(content, list):
                                for content_item in content:
                                    if isinstance(content_item, str):
                                        response_text += content_item
                                    elif hasattr(content_item, 'text') and content_item.text:
                                        response_text += content_item.text
                # Handle direct text chunks
                elif hasattr(chunk, 'text') and chunk.text:
                    logger.debug(f"Using chunk.text: {chunk.text}")
                    response_text += chunk.text
                # Handle message format
                elif hasattr(chunk, 'message') and chunk.message:
                    if hasattr(chunk.message, 'content') and chunk.message.content:
                        logger.debug(f"Using chunk.message.content: {chunk.message.content}")
                        response_text += chunk.message.content
                else:
                    logger.debug(f"Unhandled chunk format: {dir(chunk)}")
            
            if response_text:
                self.messages.append({"role": "assistant", "content": response_text})
                logger.info(f"Agent responded: {response_text}")
                if self.conversation_callback:
                    self.conversation_callback("agent", response_text)
                else:
                    print(f"🤖 ADA: {response_text}")
                return response_text
                
        except Exception as e:
            logger.error(f"LLM error: {e}")
            import traceback
            traceback.print_exc()
            return "I'm sorry, I had trouble processing that."
        finally:
            self.status.set_thinking(False)
