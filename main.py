import asyncio
import logging
from config import Config
from logger import setup_logger
from methodology_parser import MethodologyParser
from command_executor import CommandExecutor
from ai_interface import AIInterface

logger = None

async def main():
    global logger
    logger = setup_logger()
    logger.info("=== BUG BOUNTY AUTOMATOR v1.0 - NYX CORE ACTIVE ===")

    config = Config()
    parser = MethodologyParser(config.methodology_file)
    executor = CommandExecutor()
    ai = AIInterface(config.api_endpoint, config.api_key)

    phases = parser.parse()
    history = []  # List of (phase, command, output_summary)
    current_phase = phases[0]
    step = 0

    logger.info(f"Target: {config.target}")
    logger.info(f"Methodology Phases: {', '.join(phases)}")

    while True:
        step += 1
        logger.info(f"\n--- STEP {step} | PHASE: {current_phase} ---")

        # Build condensed history
        history_summary = ""
        recent_history = history[-config.max_history_lines:]
        if recent_history:
            history_summary = "\n".join([
                f"[{h[0]}] {h[1]} → {h[2][:config.max_output_chars]}{'...' if len(h[2]) > config.max_output_chars else ''}"
                for h in recent_history
            ])

        prompt = f"""
TARGET: {config.target}
CURRENT PHASE: {current_phase}
METHODOLOGY: {', '.join(phases)}
TOOLS AVAILABLE: {', '.join(config.tools)}

HISTORY:
{history_summary or "None"}

Generate the next command. Do not repeat. Escalate when ready.
"""

        logger.info("Sending to AI...")
        result = await ai.generate_command(prompt)

        if not result.get("command") or result.get("stop"):
            logger.info("AI signaled STOP or failed.")
            if "error" in result:
                logger.error(f"AI Error: {result['error']}")
            break

        command = result["command"].strip()
        next_phase = result.get("next_phase", current_phase)

        logger.info(f"AI → COMMAND: {command}")
        output = await executor.execute(command)

        # Summarize output
        output_summary = output.replace("\n", " ").strip()
        if len(output_summary) > config.max_output_chars:
            output_summary = output_summary[:config.max_output_chars] + "..."

        history.append((current_phase, command, output_summary))
        current_phase = next_phase

        # Log full output to history file
        with open("history.log", "a") as f:
            f.write(f"\n--- STEP {step} | {current_phase} ---\n")
            f.write(f"COMMAND: {command}\n")
            f.write(f"OUTPUT:\n{output}\n")

    logger.info("=== AUTOMATOR SESSION COMPLETE ===")
    logger.info(f"Total steps: {step}")
    logger.info("Check automator.log and history.log for full session.")

if __name__ == "__main__":
    asyncio.run(main())