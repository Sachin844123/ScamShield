import os
import base64
import requests
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

VIRUSTOTAL_API_KEY = os.getenv("VIRUSTOTAL_API_KEY")
VT_HEADERS = {
    "x-apikey": VIRUSTOTAL_API_KEY,
    "accept": "application/json"
}

def get_url_id(url: str) -> str:
    """Generates the VirusTotal URL identifier."""
    return base64.urlsafe_b64encode(url.encode()).decode().strip("=")

def scan_url_vt(url: str) -> Dict[str, Any]:
    """
    Checks VirusTotal for an existing report of the URL.
    If not found, submits it for scanning (though we prefer quick checks).
    Returns basic stats: malicious, suspicious, harmless, undetected.
    """
    result = {
        "malicious": False,
        "suspicious": 0,
        "malicious_count": 0,
        "harmless": 0,
        "undetected": 0,
        "details": "VirusTotal: No data",
        "link": f"https://www.virustotal.com/gui/url/{get_url_id(url)}"
    }

    if not VIRUSTOTAL_API_KEY:
        result["details"] = "VirusTotal: API Key missing"
        return result

    url_id = get_url_id(url)
    vt_url = f"https://www.virustotal.com/api/v3/urls/{url_id}"

    try:
        response = requests.get(vt_url, headers=VT_HEADERS, timeout=10)
        
        # If not found, submit for scan
        if response.status_code == 404:
            submit_url = "https://www.virustotal.com/api/v3/urls"
            submit_resp = requests.post(submit_url, headers=VT_HEADERS, data={"url": url}, timeout=10)
            if submit_resp.status_code == 200:
                result["details"] = "VirusTotal: Scan submitted (Check again in a few seconds)"
            else:
                result["details"] = f"VirusTotal: Submission failed ({submit_resp.status_code})"
            return result

        response.raise_for_status()
        data = response.json()
        
        stats = data.get("data", {}).get("attributes", {}).get("last_analysis_stats", {})
        
        result["malicious_count"] = stats.get("malicious", 0)
        result["suspicious"] = stats.get("suspicious", 0)
        result["harmless"] = stats.get("harmless", 0)
        result["undetected"] = stats.get("undetected", 0)
        
        # We consider it malicious if at least 1 engine flags it
        if result["malicious_count"] > 0:
            result["malicious"] = True
            result["details"] = f"VirusTotal: Flagged by {result['malicious_count']} engines"
        else:
            result["details"] = "VirusTotal: Clean"

    except Exception as e:
        result["details"] = f"VirusTotal Error: {str(e)}"
        print(f"VT Error: {e}")

    return result
