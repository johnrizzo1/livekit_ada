import sys
from pathlib import Path

# Add the parent directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from livekit import agents
from src.agent import entrypoint


def main():
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))


if __name__ == "__main__":
    main()
