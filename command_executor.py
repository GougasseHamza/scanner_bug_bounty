import asyncio
import logging
import os
from datetime import datetime

logger = logging.getLogger("BugBountyAutomator")

class CommandExecutor:
    def __init__(self, timeout: int = 600):
        self.timeout = timeout
        self.executed_commands = []
        
    async def execute(self, command: str) -> str:
        """Execute command with timeout and better error handling"""
        logger.info(f"Executing: {command}")
        
        # Validate command
        if not self._is_safe_command(command):
            error_msg = f"Command blocked for safety: {command}"
            logger.error(error_msg)
            return error_msg
        
        # Record execution
        self.executed_commands.append({
            "command": command,
            "timestamp": datetime.now().isoformat()
        })
        
        try:
            # Setup environment
            env = os.environ.copy()
            env["PATH"] = f"{env.get('PATH', '')}:/home/kyyblin/go/bin:/usr/local/bin"
            
            # Create subprocess
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                shell=True,
                env=env
            )
            
            # Wait with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                error_msg = f"Command timed out after {self.timeout} seconds"
                logger.warning(error_msg)
                return error_msg
            
            # Process output
            if process.returncode == 0:
                output = stdout.decode(errors='replace').strip()
            else:
                # Include both stdout and stderr for failed commands
                stdout_str = stdout.decode(errors='replace').strip()
                stderr_str = stderr.decode(errors='replace').strip()
                output = f"STDOUT:\n{stdout_str}\n\nSTDERR:\n{stderr_str}" if stdout_str else stderr_str
            
            # Handle empty output
            if not output.strip():
                output = f"[No output. Exit code: {process.returncode}]"
                logger.warning(f"Command produced no output: {command}")
            
            return output
            
        except Exception as e:
            error_msg = f"Command execution error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return error_msg
    
    def _is_safe_command(self, command: str) -> bool:
        """Basic safety check for commands"""
        # Block obviously dangerous commands
        dangerous_patterns = [
            "rm -rf /",
            ":(){ :|:& };:",  # fork bomb
            "dd if=/dev/zero",
            "mkfs.",
            "> /dev/sda",
            "wget http://",  # Block arbitrary downloads
            "curl http://",  # Block arbitrary downloads
            "nc -e",  # Reverse shells
            "/bin/bash -i",
            "/bin/sh -i"
        ]
        
        command_lower = command.lower()
        for pattern in dangerous_patterns:
            if pattern.lower() in command_lower:
                logger.error(f"Blocked dangerous command pattern: {pattern}")
                return False
        
        return True
    
    async def check_tool_available(self, tool: str) -> bool:
        """Check if a tool is available in PATH"""
        try:
            process = await asyncio.create_subprocess_shell(
                f"which {tool}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            return process.returncode == 0
        except:
            return False
    
    async def validate_tools(self, tools: list) -> dict:
        """Validate which tools are available"""
        results = {}
        for tool in tools:
            results[tool] = await self.check_tool_available(tool)
        return results