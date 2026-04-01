import asyncio
import logging
from agent.orchestrator import Orchestrator
from agent.config import settings

logging.basicConfig(level=settings.log_level)

async def main() -> None:
    orchestrator = Orchestrator()
    await orchestrator.setup()
    print("Mimi ready. Type to chat (Ctrl+C to exit).")
    session_id = "terminal"
    try:
        while True:
            text = input("\nYou: ").strip()
            if not text:
                continue
            response = await orchestrator.process_text(text, session_id=session_id)
            print(f"Mimi: {response}")
    except (KeyboardInterrupt, EOFError):
        print("\nBye!")
    finally:
        await orchestrator.teardown()

if __name__ == "__main__":
    asyncio.run(main())
