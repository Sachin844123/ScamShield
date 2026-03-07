import requests
import json

def test_analyze(url_to_test):
    api_url = "http://localhost:8000/api/analyze"
    payload = {"message": f"Check this suspicious link: {url_to_test}"}
    
    print(f"Testing Analysis with URL: {url_to_test}...")
    try:
        response = requests.post(api_url, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        print("\n--- RESULTS ---")
        print(f"Risk Score: {data.get('risk_score')}/100")
        print(f"Scam Type: {data.get('scam_type')}")
        
        url_details = data.get("urlscan_details", {})
        print(f"URL: {url_details.get('scanned_url')}")
        
        vt = url_details.get("virustotal", {})
        print(f"VirusTotal Malicious: {vt.get('malicious')}")
        print(f"VirusTotal Flags: {vt.get('malicious_count')}")
        print(f"VirusTotal Details: {vt.get('details')}")
        
        urlscan_malicious = url_details.get("malicious")
        print(f"urlscan.io Malicious: {urlscan_malicious}")
        
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    # Test with a known clean domain
    test_analyze("https://google.com")
