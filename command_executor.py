import asyncio
import logging
import os

logger = logging.getLogger("BugBountyAutomator")

class CommandExecutor:
    async def execute(self, command: str) -> str:
        logger.info(f"Executing: {command}")
        try:
            # Force include Go bin
            env = os.environ.copy()
            env["PATH"] = f"{env.get('PATH', '')}:/home/kyyblin/go/bin"
            
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                shell=True,
                env=env  # ← CRITICAL
            )
            stdout, stderr = await process.communicate()

            output = stdout.decode() if process.returncode == 0 else stderr.decode()
            if not output.strip():
                output = f"[No output. Exit code: {process.returncode}]"
            return output
        except Exception as e:
            error_msg = f"Command failed: {str(e)}"
            logger.error(error_msg)
            return error_msg