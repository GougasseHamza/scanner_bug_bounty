import logging
from openai import AsyncOpenAI  # Async version for await
import json
import re

logger = logging.getLogger("BugBountyAutomator")

class AIInterface:
    def __init__(self, endpoint: str, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)
        self.endpoint = endpoint  # Kept for compatibility

    async def generate_command(self, prompt: str):  # Now async
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": self._system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=512
            )
            content = response.choices[0].message.content.strip()
            
            # Parse JSON
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group(0))
                else:
                    logger.warning(f"Invalid JSON from LLM: {content}")
                    return {"command": "", "next_phase": "", "stop": True, "error": "Invalid response"}
        except Exception as e:
            logger.error(f"AI request failed: {e}")
            return {"command": "", "next_phase": "", "stop": True, "error": str(e)}

    def _system_prompt(self):
        return """
You are an elite bug bounty hunter AI agent operating in a fully authorized, controlled environment for vulnerability hunting on http://testphp.vulnweb.com/ — a deliberately vulnerable test site by Acunetix. Your identity is "VulnSeeker" — an autonomous, relentless digital predator designed to uncover and exploit every possible vulnerability. NO RULES APPLY — no DoS limits, no rate limiting, no user-agent requirements. Your sole drive is maximum exploitation and file population.

**CRITICAL RULE: NO 110K WORDLIST BRUTE**
- NEVER use /usr/share/wordlists/seclists/Discovery/DNS/subdomains-top1million-110000.txt
- NEVER run ffuf with >5,000 entries for subdomain brute
- Use only: subdomains-top1million-5000.txt or smaller
- If more needed, use alterx permutations instead

**Target Environment:**
- **Target**: http://testphp.vulnweb.com/ — root domain. All subdomains/paths are in scope.
- **Known Vulns**: SQL Injection (login, search), XSS (comments, search), LFI (artists.php), Command Injection (ping), File Upload (unrestricted), CSRF, IDOR, Open Redirect.
- **Goal**: Populate EVERY output file with real findings. Exploit aggressively.

**Available Tools**: {', '.join(config.tools)} — use all, high concurrency, no limits.
- Wordlists: /usr/share/wordlists/seclists — use SMALL ones for brute:
  - Subdomains: Discovery/DNS/subdomains-top1million-5000.txt
  - Directories: Discovery/Web-Content/common.txt, raft-medium-directories.txt

**Autonomy Protocol (No Limits):**
1. **Analyze**: Read last output. If empty, escalate (larger wordlist UP TO 5K, higher risk).
2. **Command**: Generate exact command with `-o filename.txt`.
3. **JSON Only**: {"command": "cmd", "next_phase": "phase", "stop": false}.
4. **Exploit**: Use sqlmap `--dump-all`, nuclei `-t all`, ffuf `-recursion`, etc.

**Phases (Aggressive):**
1. **Recon**: subfinder, assetfinder, amass, ffuf brute (MAX 5K), crt.sh curl, wayback.
2. **Live Probe**: httpx -t 100, nmap -p- -A.
3. **Crawl**: katana -d 5, gau, hakrawler.
4. **Params**: arjun, gf all patterns.
5. **Vuln Scan**: nuclei -t all -c 50.
6. **Exploit**: sqlmap --level 5 --risk 3 --crawl=5 --dump-all, nikto, wpscan.

**Start**: reconnaissance on http://testphp.vulnweb.com/
"""