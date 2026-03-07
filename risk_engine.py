import re
from typing import Dict, Any

def calculate_rule_based_score(message: str) -> int:
    """
    Applies rule-based scoring boost to the given message.
    Optimized for Indian context and obfuscated text.
    """
    score = 0
    
    # Pre-processing: Remove all whitespace and non-alphanumeric to catch "0 T P", "U R G E N T"
    msg_no_spaces = re.sub(r'[^a-zA-Z0-9]', '', message).lower()
    msg_lower = message.lower()
    
    # 1. OTP pattern (including obfuscated '0TP', 'O T P')
    if "otp" in msg_no_spaces or "0tp" in msg_no_spaces or (re.search(r'\b[0-9]{4,6}\b', msg_lower) and ("code" in msg_lower or "verification" in msg_lower)):
        score += 20
            
    # 2. Urgency (including obfuscated)
    urgency_keywords = ["urgent", "immediately", "actionrequired", "actnow", "suspended", "blocked", "turant"]
    if any(keyword in msg_no_spaces for keyword in urgency_keywords):
        score += 15
        
    # 3. UPI pattern & Financial Impersonation (India specific)
    if "upi" in msg_no_spaces or "paytm" in msg_no_spaces or "phonepe" in msg_no_spaces or "gpay" in msg_no_spaces:
        score += 25
    # Explicit regex for UPI IDs (e.g., number@upi, name@okicici)
    if re.search(r'[a-zA-Z0-9\.\-]{2,256}@[a-zA-Z][a-zA-Z]{2,64}', msg_lower):
        score += 25
            
    # 4. Shortened links & APK files
    short_link_domains = ["bit.ly", "tinyurl", "t.co", "goo.gl", "ow.ly", "is.gd", ".apk"]
    if any(domain in msg_lower for domain in short_link_domains):
        score += 15
        
    # 5. Indian Specific Scam Keywords (Reward, Extortion, KYC)
    indian_scam_keywords = [
        "kbclottery", "kaunbanegacrorepati", "mahadiscom", "electricitydisconnected",
        "sbikyc", "kycupdate", "pancardsuspension", "aadhaarblocked", "incometaxrefund"
    ]
    if any(keyword in msg_no_spaces for keyword in indian_scam_keywords):
        score += 25
        
    # 6. Threatening language
    threat_keywords = ["police", "arrest", "warrant", "fine", "penalty", "court", "fir"]
    if any(keyword in msg_no_spaces for keyword in threat_keywords):
        score += 10
        
    return score

def analyze_risk(message: str, llm_result: Dict[str, Any], url_threat: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Combines LLM score with rule-based score.
    Caps final score at 100.
    """
    rule_score = calculate_rule_based_score(message)
    base_llm_score = llm_result.get("risk_score", 0)
    
    # URL Scan Bonus
    url_boost = 0
    if url_threat and url_threat.get("malicious"):
        url_boost = 30 # Significant boost for verified malicious links
        llm_result["explanation"] += f" | {url_threat.get('details')}"
    
    final_score = base_llm_score + rule_score + url_boost
    if final_score > 100:
        final_score = 100
        
    llm_result["ai_base_score"] = base_llm_score
    llm_result["risk_score"] = final_score
    llm_result["rule_boost"] = rule_score + url_boost
    return llm_result
