# config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    def __init__(self):
        # OpenAI API
        self.api_endpoint = "https://api.openai.com/v1/chat/completions"
        self.api_key = os.getenv("OPENAI_API_KEY")
        
        # Infomaniak Target
        self.target = os.getenv("TARGET", "ksuite.infomaniak.com")
        
        # Methodology file (required by main.py)
        self.methodology_file = "methodology.txt"  # ← RESTORED
        
        # Full Tool List (All 28 tools)
        self.tools = [
            "nmap", "dirb", "sqlmap", "gobuster", "nikto",
            "ffuf", "nuclei", "feroxbuster", "whatweb", "wpscan",
            "subfinder", "assetfinder", "findomain", "amass", "github-subdomains",
            "alterx", "dnsx", "asnmap", "httpx-toolkit", "gowitness",
            "katana", "hakrawler", "gau", "urlfinder", "urldedupe",
            "gf", "arjun", "dirsearch"
        ]
        
        # History control
        self.max_history_lines = 15
        self.max_output_chars = 500