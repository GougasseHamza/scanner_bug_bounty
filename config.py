import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    def __init__(self):
        # OpenAI API
        self.api_endpoint = "https://api.openai.com/v1/chat/completions"
        self.api_key = os.getenv("OPENAI_API_KEY")
        
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        # Target Configuration
        self.target = os.getenv("TARGET", "testphp.vulnweb.com")
        
        # Methodology file
        self.methodology_file = os.getenv("METHODOLOGY_FILE", "methodology.txt")
        
        # Full Tool List
        self.tools = [
            "nmap", "dirb", "sqlmap", "gobuster", "nikto",
            "ffuf", "nuclei", "feroxbuster", "whatweb", "wpscan",
            "subfinder", "assetfinder", "findomain", "amass", "github-subdomains",
            "alterx", "dnsx", "asnmap", "httpx", "httpx-toolkit", "gowitness",
            "katana", "hakrawler", "gau", "urlfinder", "urldedupe",
            "gf", "arjun", "dirsearch", "waybackurls"
        ]
        
        # AI Configuration
        self.max_history_lines = 10  # Number of recent commands to include
        self.max_output_chars = 1000  # Max chars of output to analyze
        
        # Execution Limits
        self.max_steps = int(os.getenv("MAX_STEPS", "50"))
        self.max_consecutive_failures = int(os.getenv("MAX_FAILURES", "5"))
        self.command_timeout = int(os.getenv("COMMAND_TIMEOUT", "600"))  # 10 minutes
        
        # Output Configuration
        self.output_dir = os.getenv("OUTPUT_DIR", ".")
        self.save_full_output = os.getenv("SAVE_FULL_OUTPUT", "true").lower() == "true"
        
        # Wordlist Restrictions
        self.max_wordlist_size = 5000  # Maximum wordlist entries
        self.forbidden_wordlists = [
            "/usr/share/wordlists/seclists/Discovery/DNS/subdomains-top1million-110000.txt"
        ]
        
    def validate(self):
        """Validate configuration"""
        errors = []
        
        if not self.api_key:
            errors.append("OPENAI_API_KEY is required")
        
        if not self.target:
            errors.append("TARGET is required")
        
        if not os.path.exists(self.methodology_file):
            errors.append(f"Methodology file not found: {self.methodology_file}")
        
        if errors:
            raise ValueError(f"Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors))
        
        return True