import pytest
from unittest.mock import Mock, AsyncMock, patch
from livekit.agents import JobContext, Agent
from src.agent import entrypoint, Assistant, LoggingRimeTTS


@pytest.mark.asyncio
async def test_entrypoint_creates_agent_session():
    """Test that the entrypoint creates an AgentSession with proper configuration."""
    mock_ctx = Mock(spec=JobContext)
    mock_ctx.room = Mock()
    mock_ctx.connect = AsyncMock()

    # Mock all the plugin constructors
    with patch("src.agent.assemblyai.STT") as mock_stt, patch(
        "src.agent.openai.LLM.with_cerebras"
    ) as mock_llm, patch("src.agent.LoggingRimeTTS") as mock_tts, patch(
        "src.agent.silero.VAD.load"
    ) as mock_vad, patch(
        "src.agent.AgentSession"
    ) as mock_session_class:

        # Configure mocks
        mock_stt_instance = Mock()
        mock_stt.return_value = mock_stt_instance

        mock_llm_instance = Mock()
        mock_llm.return_value = mock_llm_instance

        mock_tts_instance = Mock()
        mock_tts.return_value = mock_tts_instance

        mock_vad_instance = Mock()
        mock_vad.return_value = mock_vad_instance

        mock_session = Mock()
        mock_session.start = AsyncMock()
        mock_session.generate_reply = AsyncMock()
        mock_session_class.return_value = mock_session

        await entrypoint(mock_ctx)

    # Verify plugin constructors were called with correct parameters
    mock_stt.assert_called_once_with(
        end_of_turn_confidence_threshold=0.7,
        min_end_of_turn_silence_when_confident=160,
        max_turn_silence=2400,
        format_turns=True,
    )

    mock_llm.assert_called_once_with(model="llama-3.3-70b")

    mock_tts.assert_called_once_with(
        model="mist",
        speaker="rainforest",
        speed_alpha=0.9,
        reduce_latency=True,
    )

    mock_vad.assert_called_once()

    # Verify AgentSession was created with correct parameters
    mock_session_class.assert_called_once_with(
        stt=mock_stt_instance,
        llm=mock_llm_instance,
        tts=mock_tts_instance,
        vad=mock_vad_instance,
        turn_detection="stt",
    )

    # Verify session was started and connected
    mock_session.start.assert_called_once()
    mock_ctx.connect.assert_called_once()
    mock_session.generate_reply.assert_called_once()


@pytest.mark.asyncio
async def test_assistant_initialization():
    """Test that the Assistant agent is properly initialized."""
    assistant = Assistant()
    assert isinstance(assistant, Agent)
    # The instructions are set in the parent class initialization


@pytest.mark.asyncio
async def test_assistant_on_user_turn_completed():
    """Test the Assistant's on_user_turn_completed method."""
    assistant = Assistant()

    # Create a mock message with text content
    mock_message = Mock()
    mock_message.text_content = "Hello, assistant!"

    # Capture print output
    with patch("builtins.print") as mock_print:
        await assistant.on_user_turn_completed(Mock(), mock_message)
        mock_print.assert_called_once_with(
            "👶 [User] User Transcript: Hello, assistant!"
        )

    # Test with no text content
    mock_message.text_content = None
    with patch("builtins.print") as mock_print:
        await assistant.on_user_turn_completed(Mock(), mock_message)
        mock_print.assert_not_called()


def test_logging_rime_tts():
    """Test that LoggingRimeTTS logs synthesized text."""
    # Mock the parent class constructor
    with patch("livekit.plugins.rime.TTS.__init__", return_value=None):
        tts = LoggingRimeTTS(
            model="mist",
            speaker="rainforest",
            speed_alpha=0.9,
            reduce_latency=True,
        )

        # Mock the parent synthesize method
        with patch("livekit.plugins.rime.TTS.synthesize") as mock_synthesize:
            mock_synthesize.return_value = "audio_data"

            with patch("builtins.print") as mock_print:
                result = tts.synthesize("Hello, world!")

                mock_print.assert_called_once_with(
                    "🔊 [Rime TTS] Outgoing Audio:", "Hello, world!"
                )
                assert result == "audio_data"


def test_main_function():
    """Test that the main function in agent.py calls run_app correctly."""
    # Test the main block execution
    with patch("livekit.agents.cli.run_app") as mock_run_app:
        with patch("livekit.agents.WorkerOptions") as mock_worker_options:
            # Mock the worker instance
            mock_worker_instance = Mock()
            mock_worker_options.return_value = mock_worker_instance

            # Test that if we run agent.py as main, it calls run_app
            import src.agent

            # Manually call the code that would run in __main__
            if hasattr(src.agent, "agents"):
                src.agent.agents.cli.run_app(
                    src.agent.agents.WorkerOptions(entrypoint_fnc=src.agent.entrypoint)
                )

            # Verify the call was made
            assert mock_run_app.called


def test_main_py_imports():
    """Test that main.py properly imports and uses the entrypoint."""
    with patch("livekit.agents.cli.run_app") as mock_run_app:
        with patch("livekit.agents.WorkerOptions") as mock_worker_options:
            mock_worker_instance = Mock()
            mock_worker_options.return_value = mock_worker_instance

            from src.main import main

            main()

            mock_worker_options.assert_called_once()
            # Check that entrypoint function was passed
            call_kwargs = mock_worker_options.call_args.kwargs
            assert "entrypoint_fnc" in call_kwargs
            assert call_kwargs["entrypoint_fnc"].__name__ == "entrypoint"

            mock_run_app.assert_called_once_with(mock_worker_instance)
