import os
import re
import time
import requests
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

URLSCAN_API_KEY = os.getenv("URLSCAN_API_KEY", "019ca541-d77e-775e-b9e0-636bb33af590")
HEADERS = {
    "API-Key": URLSCAN_API_KEY,
    "Content-Type": "application/json"
}

def extract_first_url(text: str) -> Optional[str]:
    """Finds the first http/https URL in the text."""
    url_pattern = r"(https?://[^\s]+)"
    match = re.search(url_pattern, text)
    return match.group(1) if match else None

def scan_and_analyze_url(url: str) -> Dict[str, Any]:
    """
    Submits a URL to urlscan.io, waits, and fetches the result including screenshot.
    Returns: {"malicious": bool, "score": int, "details": str, "screenshot_url": str}
    """
    result = {
        "scanned_url": url, 
        "malicious": False, 
        "score": 0, 
        "details": "Safe or unclassified", 
        "screenshot_url": None,
        "ip": "Unknown",
        "domain": "Unknown",
        "ssl": "Unknown"
    }
    
    try:
        # Step 1: Submit Scan
        submit_url = "https://urlscan.io/api/v1/scan/"
        payload = {"url": url, "visibility": "public"}
        
        submit_resp = requests.post(submit_url, headers=HEADERS, json=payload, timeout=10)
        submit_resp.raise_for_status()
        
        submit_data = submit_resp.json()
        scan_uuid = submit_data.get("uuid")
        
        if not scan_uuid:
            return result
        
        # Step 2: Wait for processing (8-10 seconds)
        time.sleep(10)
        
        # Step 3: Fetch Result
        result_url = f"https://urlscan.io/api/v1/result/{scan_uuid}/"
        res = requests.get(result_url, timeout=10)
        
        if res.status_code == 200:
            data = res.json()
            verdicts = data.get("verdicts", {}).get("overall", {})
            
            is_malicious = verdicts.get("malicious", False)
            score = verdicts.get("score", 0)
            
            # Extract Screenshot
            screenshot_url = data.get("task", {}).get("screenshotURL")
            # Fallback if task.screenshotURL isn't populated but the structure exists
            if not screenshot_url:
                screenshot_url = f"https://urlscan.io/screenshots/{scan_uuid}.png"
                
            # Extract Extra Info
            page = data.get("page", {})
            result["ip"] = page.get("ip", "Unknown")
            result["domain"] = page.get("domain", "Unknown")
            result["ssl"] = "Valid" if page.get("tlsValid") else "Invalid/None"
            
            result["screenshot_url"] = screenshot_url
            result["malicious"] = is_malicious
            result["score"] = score
            if is_malicious:
                result["details"] = f"urlscan.io flagged as malicious (Score: {score})"
                
    except Exception as e:
        print(f"URLScan Error: {str(e)}")
        
    return result

from virustotal_service import scan_url_vt

def process_message_urls(message: str) -> Dict[str, Any]:
    """Extracts URL and checks risk using both urlscan.io and VirusTotal."""
    extracted_url = extract_first_url(message)
    if not extracted_url:
        return {"scanned_url": None, "malicious": False, "score": 0, "details": "No URL found"}
    
    # 1. Start urlscan.io (for screenshot and their verdict)
    urlscan_res = scan_and_analyze_url(extracted_url)
    
    # 2. Start VirusTotal analysis (secondary threat source)
    vt_res = scan_url_vt(extracted_url)
    
    # 3. Combine Verdicts
    combined_score = max(urlscan_res.get("score", 0), (vt_res.get("malicious_count", 0) * 10))
    is_malicious = urlscan_res.get("malicious", False) or vt_res.get("malicious", False)
    
    # Merge reports
    urlscan_res["virustotal"] = vt_res
    if vt_res.get("malicious"):
        urlscan_res["malicious"] = True
        urlscan_res["score"] = min(combined_score, 100)
        urlscan_res["details"] += f" | {vt_res.get('details')}"
        
    return urlscan_res
