import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from database import engine, init_db, SessionLocal, MessageLog
from ai_engine import analyze_message_with_llm
from risk_engine import analyze_risk
from urlscan_service import process_message_urls

app = FastAPI(title="ScamShield API")

init_db()

templates = Jinja2Templates(directory="templates")

class BotRequest(BaseModel):
    message: str

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "result": None})

@app.post("/analyze", response_class=HTMLResponse)
async def analyze_web(request: Request, message: str = Form(...)):
    db = SessionLocal()
    try:
        # 1. URL Scanning
        url_threat = process_message_urls(message)
        urlscan_boost = 0
        if url_threat.get("malicious"):
            urlscan_boost = 25
            
        # 2. LLM Analysis
        try:
            llm_result = analyze_message_with_llm(message)
        except Exception as e:
            return templates.TemplateResponse("index.html", {
                "request": request, 
                "message": message,
                "error": str(e)
            })
            
        # 3. Hybrid Scoring
        final_result = analyze_risk(message, llm_result)
        
        # Inject URLScan bursts and Screenshot
        if urlscan_boost > 0:
            final_result["rule_boost"] = final_result.get("rule_boost", 0) + urlscan_boost
            
            new_final_score = final_result.get("ai_base_score", 0) + final_result.get("rule_boost", 0)
            final_result["risk_score"] = min(new_final_score, 100)
            
            final_result["explanation"] += f" ⚠️ SECURITY ALERT: Connected link verified externally as malicious."
            
        final_result["urlscan_details"] = url_threat
        if url_threat.get("screenshot_url"):
            final_result["screenshot_url"] = url_threat["screenshot_url"]
            
        # Save to DB
        new_log = MessageLog(
            original_message=message,
            detected_language=final_result.get("language", "Unknown"),
            risk_score=final_result.get("risk_score"),
            scam_type=final_result.get("scam_type"),
            psychological_trick=final_result.get("psychological_trick")
        )
        db.add(new_log)
        db.commit()
        
        return templates.TemplateResponse("index.html", {
            "request": request,
            "message": message,
            "result": final_result
        })
    finally:
        db.close()

@app.post("/api/analyze")
async def analyze_api(req: BotRequest):
    db = SessionLocal()
    try:
        # 1. URL Scanning (Optional Blocking Intelligence)
        url_threat = process_message_urls(req.message)
        urlscan_boost = 0
        if url_threat.get("malicious"):
            urlscan_boost = 25
            
        # 2. LLM Analysis
        llm_result = analyze_message_with_llm(req.message)
        
        # 3. Hybrid Scoring
        final_result = analyze_risk(req.message, llm_result)
        
        # Inject URLScan boosts into final payload
        if urlscan_boost > 0:
            final_result["rule_boost"] = final_result.get("rule_boost", 0) + urlscan_boost
            
            # Recalculate and cap final score
            new_final_score = final_result.get("ai_base_score", 0) + final_result.get("rule_boost", 0)
            final_result["risk_score"] = min(new_final_score, 100)
            
            # Append explanation
            final_result["explanation"] += f" WARNING: Attached link was flagged globally as a known malicious URL by urlscan.io."
            
        final_result["urlscan_details"] = url_threat
        if url_threat.get("screenshot_url"):
            final_result["screenshot_url"] = url_threat["screenshot_url"]
            
        # Save to DB
        new_log = MessageLog(
            original_message=req.message,
            detected_language=final_result.get("language", "Unknown"),
            risk_score=final_result.get("risk_score"),
            scam_type=final_result.get("scam_type"),
            psychological_trick=final_result.get("psychological_trick")
        )
        db.add(new_log)
        db.commit()
        
        return final_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
