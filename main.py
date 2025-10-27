import asyncio
import json 
import logging
from datetime import datetime
from pathlib import Path
from config import Config
from logger import setup_logger
from methodology_parser import MethodologyParser
from command_executor import CommandExecutor
from ai_interface import AIInterface
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from rich import box

console = Console()
logger = None

class BugBountyAutomator:
    def __init__(self):
        self.config = Config()
        self.parser = MethodologyParser(self.config.methodology_file)
        self.executor = CommandExecutor()
        self.ai = AIInterface(self.config.api_endpoint, self.config.api_key)
        self.history = []
        self.session_start = datetime.now()
        self.findings = {
            "vulnerabilities": [],
            "interesting_findings": [],
            "live_hosts": [],
            "subdomains": []
        }

    async def run(self):
        """Main execution loop"""
        console.print(Panel.fit(
            "[bold cyan]🎯 BUG BOUNTY AUTOMATOR v2.0[/bold cyan]\n"
            f"[yellow]Target:[/yellow] {self.config.target}\n"
            f"[yellow]Started:[/yellow] {self.session_start.strftime('%Y-%m-%d %H:%M:%S')}",
            border_style="cyan"
        ))

        phases = self.parser.parse()
        current_phase = phases[0]
        step = 0
        max_steps = 50  # Safety limit
        consecutive_failures = 0
        max_failures = 5

        logger.info(f"Target: {self.config.target}")
        logger.info(f"Methodology Phases: {', '.join(phases)}")

        while step < max_steps and consecutive_failures < max_failures:
            step += 1
            
            # Display step header
            self._display_step_header(step, current_phase)

            # Build AI prompt with full context
            prompt = self._build_prompt(current_phase, phases)

            # Get next command from AI
            with Progress(
                SpinnerColumn(),
                TextColumn("[cyan]AI thinking..."),
                console=console
            ) as progress:
                task = progress.add_task("generating", total=None)
                result = await self.ai.generate_command(prompt)

            # Check for stop condition
            if not result.get("command") or result.get("stop"):
                self._handle_stop(result, step)
                break

            command = result["command"].strip()
            next_phase = result.get("next_phase", current_phase)
            reasoning = result.get("reasoning", "No reasoning provided")

            # Display command info
            self._display_command(command, reasoning)

            # Execute command
            with Progress(
                SpinnerColumn(),
                TextColumn(f"[yellow]Executing: {command[:60]}..."),
                console=console
            ) as progress:
                task = progress.add_task("executing", total=None)
                output = await self.executor.execute(command)

            # Check if command succeeded
            success = self._check_command_success(output)
            
            if not success:
                consecutive_failures += 1
                console.print(f"[red]⚠ Command failed or produced no output ({consecutive_failures}/{max_failures})[/red]")
            else:
                consecutive_failures = 0

            # Analyze output with AI
            console.print("\n[cyan]📊 Analyzing output...[/cyan]")
            analysis = await self.ai.analyze_output(command, output, current_phase)
            
            # Display analysis
            self._display_analysis(analysis, output)

            # Update findings
            self._update_findings(analysis, output)

            # Store in history
            self.history.append({
                "step": step,
                "phase": current_phase,
                "command": command,
                "output": output,
                "analysis": analysis,
                "success": success,
                "timestamp": datetime.now().isoformat()
            })

            # Log to file
            self._log_to_file(step, current_phase, command, output, analysis)

            # Update phase
            current_phase = next_phase

            # Brief pause between commands
            await asyncio.sleep(1)

        # Display session summary
        self._display_summary(step)

    def _build_prompt(self, current_phase: str, phases: list) -> str:
        """Build comprehensive prompt for AI with full context"""
        # Get recent history with analysis
        recent_history = self.history[-self.config.max_history_lines:]
        
        history_text = ""
        if recent_history:
            history_entries = []
            for h in recent_history:
                analysis = h.get("analysis", {})
                findings = ", ".join(analysis.get("findings", [])[:3])
                history_entries.append(
                    f"[{h['phase']}] {h['command']}\n"
                    f"  ↳ Success: {h['success']}, Findings: {findings or 'None'}\n"
                    f"  ↳ Output: {h['output'][:300]}..."
                )
            history_text = "\n".join(history_entries)

        prompt = f"""
TARGET: {self.config.target}
CURRENT PHASE: {current_phase}
METHODOLOGY: {', '.join(phases)}
STEP: {len(self.history) + 1}

TOOLS AVAILABLE: {', '.join(self.config.tools)}

ACCUMULATED FINDINGS:
- Vulnerabilities: {len(self.findings['vulnerabilities'])}
- Live Hosts: {len(self.findings['live_hosts'])}
- Subdomains: {len(self.findings['subdomains'])}

RECENT COMMAND HISTORY WITH ANALYSIS:
{history_text or "No history yet - this is the first command"}

INSTRUCTIONS:
1. Analyze the RECENT COMMAND HISTORY carefully
2. Check what worked and what failed
3. Avoid repeating failed commands
4. Generate the next logical command based on findings
5. Escalate techniques when appropriate
6. Move to next phase when current phase is exhausted

Respond with valid JSON only.
"""
        return prompt

    def _display_step_header(self, step: int, phase: str):
        """Display step header in console"""
        console.print(f"\n{'='*80}")
        console.print(f"[bold green]STEP {step}[/bold green] | [bold yellow]PHASE: {phase.upper()}[/bold yellow]")
        console.print(f"{'='*80}\n")
        logger.info(f"\n--- STEP {step} | PHASE: {phase} ---")

    def _display_command(self, command: str, reasoning: str):
        """Display command and reasoning"""
        console.print(Panel(
            f"[bold cyan]Command:[/bold cyan]\n{command}\n\n"
            f"[bold yellow]Reasoning:[/bold yellow]\n{reasoning}",
            title="🤖 AI Decision",
            border_style="green"
        ))
        logger.info(f"AI → COMMAND: {command}")
        logger.info(f"AI → REASONING: {reasoning}")

    def _display_analysis(self, analysis: dict, output: str):
        """Display AI analysis of output"""
        # Create analysis table
        table = Table(title="📊 Output Analysis", box=box.ROUNDED)
        table.add_column("Category", style="cyan", no_wrap=True)
        table.add_column("Details", style="white")

        # Summary
        table.add_row("Summary", analysis.get("summary", "N/A"))
        
        # Risk Level
        risk = analysis.get("risk_level", "unknown")
        risk_color = {
            "low": "green",
            "medium": "yellow",
            "high": "red",
            "critical": "bold red"
        }.get(risk, "white")
        table.add_row("Risk Level", f"[{risk_color}]{risk.upper()}[/{risk_color}]")

        # Findings
        findings = analysis.get("findings", [])
        if findings:
            findings_text = "\n".join([f"• {f}" for f in findings[:5]])
            table.add_row("Findings", findings_text)

        # Vulnerabilities
        vulns = analysis.get("vulnerabilities", [])
        if vulns:
            vulns_text = "\n".join([f"🔴 {v}" for v in vulns[:3]])
            table.add_row("Vulnerabilities", vulns_text)

        # Next Actions
        actions = analysis.get("next_actions", [])
        if actions:
            actions_text = "\n".join([f"→ {a}" for a in actions[:3]])
            table.add_row("Next Actions", actions_text)

        console.print(table)

        # Show output snippet
        output_preview = output[:500] if output else "[No output]"
        console.print(Panel(
            output_preview,
            title="📄 Output Preview (first 500 chars)",
            border_style="blue"
        ))

    def _check_command_success(self, output: str) -> bool:
        """Determine if command was successful"""
        if not output or output.strip() == "":
            return False
        
        # Common failure indicators
        failure_indicators = [
            "command not found",
            "no such file",
            "permission denied",
            "error:",
            "failed to",
            "[no output. exit code:",
            "usage:"
        ]
        
        output_lower = output.lower()
        for indicator in failure_indicators:
            if indicator in output_lower:
                return False
        
        return True

    def _update_findings(self, analysis: dict, output: str):
        """Update accumulated findings"""
        # Add vulnerabilities
        for vuln in analysis.get("vulnerabilities", []):
            if vuln not in self.findings["vulnerabilities"]:
                self.findings["vulnerabilities"].append(vuln)

        # Extract live hosts from httpx output
        if "http" in output.lower():
            lines = output.split("\n")
            for line in lines:
                if line.startswith("http"):
                    if line not in self.findings["live_hosts"]:
                        self.findings["live_hosts"].append(line.strip())

        # Extract subdomains
        if "subdomain" in output.lower() or ".com" in output:
            lines = output.split("\n")
            for line in lines:
                if "." in line and len(line.strip()) > 0:
                    potential_domain = line.strip()
                    if potential_domain not in self.findings["subdomains"]:
                        self.findings["subdomains"].append(potential_domain)

    def _log_to_file(self, step: int, phase: str, command: str, output: str, analysis: dict):
        """Log detailed information to file"""
        with open("history.log", "a") as f:
            f.write(f"\n{'='*100}\n")
            f.write(f"STEP {step} | PHASE: {phase} | TIME: {datetime.now()}\n")
            f.write(f"{'='*100}\n")
            f.write(f"COMMAND:\n{command}\n\n")
            f.write(f"ANALYSIS:\n{json.dumps(analysis, indent=2)}\n\n")
            f.write(f"OUTPUT:\n{output}\n")

    def _handle_stop(self, result: dict, step: int):
        """Handle stop condition"""
        console.print("\n[yellow]🛑 AI signaled completion or encountered issue[/yellow]")
        if "error" in result:
            console.print(f"[red]Error: {result['error']}[/red]")
            logger.error(f"AI Error: {result['error']}")
        logger.info("=== AUTOMATOR SESSION COMPLETE ===")

    def _display_summary(self, total_steps: int):
        """Display final summary"""
        duration = datetime.now() - self.session_start
        
        summary_table = Table(title="📈 Session Summary", box=box.DOUBLE)
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Value", style="green")
        
        summary_table.add_row("Total Steps", str(total_steps))
        summary_table.add_row("Duration", str(duration).split('.')[0])
        summary_table.add_row("Vulnerabilities Found", str(len(self.findings["vulnerabilities"])))
        summary_table.add_row("Live Hosts", str(len(self.findings["live_hosts"])))
        summary_table.add_row("Subdomains", str(len(self.findings["subdomains"])))
        
        console.print("\n")
        console.print(summary_table)
        
        if self.findings["vulnerabilities"]:
            console.print("\n[bold red]🔴 VULNERABILITIES:[/bold red]")
            for vuln in self.findings["vulnerabilities"][:10]:
                console.print(f"  • {vuln}")
        
        console.print(f"\n[cyan]📁 Full logs saved to: automator.log and history.log[/cyan]")
        logger.info(f"Total steps: {total_steps}")
        logger.info(f"Duration: {duration}")

async def main():
    global logger
    logger = setup_logger()
    
    automator = BugBountyAutomator()
    
    try:
        await automator.run()
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠ Interrupted by user[/yellow]")
        logger.warning("Session interrupted by user")
    except Exception as e:
        console.print(f"\n[red]❌ Fatal error: {e}[/red]")
        logger.error(f"Fatal error: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())