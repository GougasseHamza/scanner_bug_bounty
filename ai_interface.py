import logging
from openai import AsyncOpenAI
import json
import re

logger = logging.getLogger("BugBountyAutomator")

class AIInterface:
    def __init__(self, endpoint: str, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)
        self.endpoint = endpoint

    async def generate_command(self, prompt: str, retry_count: int = 3):
        """Generate command with retry logic and better error handling"""
        for attempt in range(retry_count):
            try:
                response = await self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": self._system_prompt()},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=1024,
                    response_format={"type": "json_object"}  # Force JSON response
                )
                content = response.choices[0].message.content.strip()
                
                # Parse JSON with robust handling
                try:
                    result = json.loads(content)
                    # Validate required fields
                    if not self._validate_response(result):
                        logger.warning(f"Invalid response structure on attempt {attempt + 1}")
                        continue
                    return result
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON decode error on attempt {attempt + 1}: {e}")
                    # Try to extract JSON from markdown code blocks
                    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
                    if json_match:
                        result = json.loads(json_match.group(1))
                        if self._validate_response(result):
                            return result
                    
                    # Try to find any JSON object
                    json_match = re.search(r'\{.*\}', content, re.DOTALL)
                    if json_match:
                        result = json.loads(json_match.group(0))
                        if self._validate_response(result):
                            return result
                    
                    if attempt == retry_count - 1:
                        logger.error(f"Could not parse JSON after {retry_count} attempts: {content}")
                        return self._error_response("Invalid JSON format")
                        
            except Exception as e:
                logger.error(f"AI request failed on attempt {attempt + 1}: {e}")
                if attempt == retry_count - 1:
                    return self._error_response(str(e))
        
        return self._error_response("Max retries exceeded")

    async def analyze_output(self, command: str, output: str, phase: str):
        """Analyze command output and provide insights"""
        try:
            analysis_prompt = f"""
Analyze this security tool output and provide actionable insights:

PHASE: {phase}
COMMAND: {command}
OUTPUT (truncated if long):
{output[:3000]}

Provide a JSON response with:
{{
    "findings": ["list of important findings"],
    "vulnerabilities": ["specific vulnerabilities found"],
    "next_actions": ["recommended next steps"],
    "risk_level": "low/medium/high/critical",
    "summary": "brief summary of what was discovered"
}}
"""
            
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a security analysis expert. Analyze tool outputs and provide actionable insights."},
                    {"role": "user", "content": analysis_prompt}
                ],
                temperature=0.2,
                max_tokens=800,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content.strip()
            analysis = json.loads(content)
            return analysis
            
        except Exception as e:
            logger.error(f"Output analysis failed: {e}")
            return {
                "findings": [],
                "vulnerabilities": [],
                "next_actions": ["Continue with next phase"],
                "risk_level": "unknown",
                "summary": "Analysis unavailable"
            }

    def _validate_response(self, result: dict) -> bool:
        """Validate that response has required structure"""
        if not isinstance(result, dict):
            return False
        
        # Check for required fields
        if "command" not in result:
            return False
            
        # If stop is True, command can be empty
        if result.get("stop", False):
            return True
            
        # Otherwise command must not be empty
        if not result["command"] or not isinstance(result["command"], str):
            return False
            
        return True

    def _error_response(self, error_msg: str) -> dict:
        """Generate standard error response"""
        return {
            "command": "",
            "next_phase": "",
            "stop": True,
            "error": error_msg
        }

    def _system_prompt(self):
        return """
You are an elite bug bounty hunter AI agent. You must respond ONLY with valid JSON.

**CRITICAL RULES:**
1. ALWAYS respond with valid JSON in this exact format:
{
    "command": "exact command to execute",
    "next_phase": "phase name for next iteration",
    "stop": false,
    "reasoning": "brief explanation of why this command"
}

2. NEVER use wordlists larger than 5000 entries for subdomain enumeration
3. NEVER use /usr/share/wordlists/seclists/Discovery/DNS/subdomains-top1million-110000.txt
4. Analyze previous command outputs carefully before generating next command
5. Do not repeat commands that already failed or produced empty results
6. Escalate techniques when basic enumeration is complete
7. Set "stop": true when no further enumeration is needed or max attempts reached

**Available Phases:**
- reconnaissance: subdomain discovery, DNS enumeration
- scanning: port scanning, service detection, directory bruteforce
- exploitation: vulnerability scanning, sqlmap, nikto, nuclei

**Tool Guidelines:**
- subfinder, assetfinder, amass: passive subdomain enumeration
- ffuf: use with small wordlists (<5000 entries), add -mc flag for status codes
- httpx: probe live hosts with -t 100 for concurrency
- nmap: -p- for full port scan, -A for service detection
- katana: crawl with -d 3-5 depth
- nuclei: use specific template categories (-t cves/, -t misconfiguration/)
- sqlmap: start with --level 2 --risk 1, escalate if needed
- arjun: parameter discovery
- nikto: web server scanning

**Output Analysis:**
Before generating next command, analyze:
- Did previous command find anything?
- Are results empty or failed?
- Should we try different approach or escalate?
- Have we exhausted this phase?

**Example Response:**
{
    "command": "subfinder -d target.com -o subdomains.txt",
    "next_phase": "reconnaissance",
    "stop": false,
    "reasoning": "Starting with passive subdomain enumeration"
}
"""