import os
import uuid
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional
import datetime

from database import engine, init_db, SessionLocal, MessageLog, HoneypotSession, HoneypotMessage
from ai_engine import analyze_message_with_llm, generate_honeypot_continuation
from risk_engine import analyze_risk
from urlscan_service import process_message_urls

app = FastAPI(
    title="ScamShield API",
    description="AI-powered scam detection for India — AWS Bedrock + Groq Hybrid",
    version="2.0.0"
)

init_db()

templates = Jinja2Templates(directory="templates")


class BotRequest(BaseModel):
    message: str


class HoneypotSessionCreate(BaseModel):
    scan_log_id: Optional[int] = None
    source: str = "web"


class HoneypotMessageCreate(BaseModel):
    sender: str   # "user" | "scammer"
    content: str


# ─── Health Check (required for Elastic Beanstalk) ────────────────────────────
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "ScamShield API",
        "version": "2.0.0",
        "ai_engine": "AWS Bedrock Claude 3.5 Sonnet + Groq Fallback",
        "database": "RDS PostgreSQL" if "postgresql" in os.getenv("DATABASE_URL", "") else "SQLite"
    }


# ─── Web Frontend ─────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "result": None})


@app.post("/analyze", response_class=HTMLResponse)
async def analyze_web(request: Request, message: str = Form(...)):
    db = SessionLocal()
    try:
        url_threat = process_message_urls(message)
        urlscan_boost = 25 if url_threat.get("malicious") else 0

        try:
            llm_result = analyze_message_with_llm(message)
        except Exception as e:
            return templates.TemplateResponse("index.html", {
                "request": request, "message": message, "error": str(e)
            })

        final_result = analyze_risk(message, llm_result, url_threat=url_threat)

        final_result["urlscan_details"] = url_threat
        if url_threat.get("screenshot_url"):
            final_result["screenshot_url"] = url_threat["screenshot_url"]

        log_id = _save_log(db, message, final_result)

        # Auto-create honeypot session for high-risk scans
        if final_result.get("risk_score", 0) > 70 and final_result.get("honeypot_reply"):
            _create_honeypot_session(
                db=db,
                scan_log_id=log_id,
                scam_type=final_result.get("scam_type"),
                risk_score=final_result.get("risk_score"),
                source="web",
                original_message=message,
                ai_honeypot_reply=final_result.get("honeypot_reply")
            )

        return templates.TemplateResponse("index.html", {
            "request": request, "message": message, "result": final_result
        })
    finally:
        db.close()


# ─── Bot/API Endpoint ─────────────────────────────────────────────────────────
@app.post("/api/analyze")
async def analyze_api(req: BotRequest):
    db = SessionLocal()
    try:
        url_threat = process_message_urls(req.message)
        urlscan_boost = 25 if url_threat.get("malicious") else 0

        llm_result = analyze_message_with_llm(req.message)
        final_result = analyze_risk(req.message, llm_result, url_threat=url_threat)

        final_result["urlscan_details"] = url_threat
        if url_threat.get("screenshot_url"):
            final_result["screenshot_url"] = url_threat["screenshot_url"]

        log_id = _save_log(db, req.message, final_result)

        # Auto-create honeypot session for high-risk scans from bot
        session_token = None
        if final_result.get("risk_score", 0) > 70 and final_result.get("honeypot_reply"):
            session_token = _create_honeypot_session(
                db=db,
                scan_log_id=log_id,
                scam_type=final_result.get("scam_type"),
                risk_score=final_result.get("risk_score"),
                source="bot",
                original_message=req.message,
                ai_honeypot_reply=final_result.get("honeypot_reply")
            )

        if session_token:
            final_result["honeypot_session_token"] = session_token

        return final_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# ─── Analytics Endpoint (Hackathon bonus: live stats) ─────────────────────────
@app.get("/api/stats")
async def get_stats():
    db = SessionLocal()
    try:
        from sqlalchemy import func
        total = db.query(func.count(MessageLog.id)).scalar()
        high_risk = db.query(func.count(MessageLog.id)).filter(MessageLog.risk_score > 70).scalar()
        avg_score = db.query(func.avg(MessageLog.risk_score)).scalar()
        top_scam_type = (
            db.query(MessageLog.scam_type, func.count(MessageLog.scam_type).label("cnt"))
            .group_by(MessageLog.scam_type)
            .order_by(func.count(MessageLog.scam_type).desc())
            .first()
        )
        # Honeypot stats
        total_sessions = db.query(func.count(HoneypotSession.id)).scalar()
        return {
            "total_scans": total or 0,
            "high_risk_scans": high_risk or 0,
            "detection_rate_pct": round((high_risk / total * 100) if total else 0, 1),
            "avg_risk_score": round(float(avg_score), 1) if avg_score else 0,
            "top_scam_type": top_scam_type[0] if top_scam_type else "N/A",
            "honeypot_sessions": total_sessions or 0,
        }
    finally:
        db.close()


# ─── Dashboard Page ───────────────────────────────────────────────────────────
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


# ─── Honeypot API ─────────────────────────────────────────────────────────────

@app.get("/api/honeypot/sessions")
async def list_sessions():
    """List all honeypot sessions (summary view)."""
    db = SessionLocal()
    try:
        from sqlalchemy import func
        sessions = (
            db.query(HoneypotSession)
            .order_by(HoneypotSession.started_at.desc())
            .limit(200)
            .all()
        )
        result = []
        for s in sessions:
            msg_count = db.query(func.count(HoneypotMessage.id)).filter(
                HoneypotMessage.session_token == s.session_token
            ).scalar()
            result.append({
                "session_token": s.session_token,
                "scam_type": s.scam_type or "Unknown",
                "risk_score": s.risk_score or 0,
                "source": s.source or "web",
                "status": s.status or "active",
                "message_count": msg_count or 0,
                "started_at": s.started_at.isoformat() if s.started_at else None,
            })
        return result
    finally:
        db.close()


@app.get("/api/honeypot/session/{token}")
async def get_session(token: str):
    """Get a single honeypot session with full message thread."""
    db = SessionLocal()
    try:
        session = db.query(HoneypotSession).filter(HoneypotSession.session_token == token).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        messages = (
            db.query(HoneypotMessage)
            .filter(HoneypotMessage.session_token == token)
            .order_by(HoneypotMessage.timestamp.asc())
            .all()
        )
        return {
            "session_token": session.session_token,
            "scam_type": session.scam_type,
            "risk_score": session.risk_score,
            "source": session.source,
            "status": session.status,
            "original_message": session.original_message,
            "ai_honeypot_reply": session.ai_honeypot_reply,
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "messages": [
                {
                    "id": m.id,
                    "sender": m.sender,
                    "content": m.content,
                    "timestamp": m.timestamp.isoformat() if m.timestamp else None,
                }
                for m in messages
            ],
        }
    finally:
        db.close()


@app.post("/api/honeypot/session")
async def create_session(req: HoneypotSessionCreate):
    """Manually create a honeypot session (used by bot for direct creation)."""
    db = SessionLocal()
    try:
        token = str(uuid.uuid4())
        session = HoneypotSession(
            session_token=token,
            scan_log_id=req.scan_log_id,
            source=req.source,
        )
        db.add(session)
        db.commit()
        return {"session_token": token}
    finally:
        db.close()


@app.post("/api/honeypot/session/{token}/message")
async def add_message(token: str, req: HoneypotMessageCreate):
    """Add a message to an existing honeypot session."""
    db = SessionLocal()
    try:
        session = db.query(HoneypotSession).filter(HoneypotSession.session_token == token).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        msg = HoneypotMessage(
            session_token=token,
            sender=req.sender,
            content=req.content,
        )
        db.add(msg)
        # Update session timestamp
        session.updated_at = datetime.datetime.utcnow()
        db.commit()
        return {"ok": True, "id": msg.id}
    finally:
        db.close()


@app.patch("/api/honeypot/session/{token}/close")
async def close_session(token: str):
    """Mark a honeypot session as closed."""
    db = SessionLocal()
    try:
        session = db.query(HoneypotSession).filter(HoneypotSession.session_token == token).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        session.status = "closed"
        session.updated_at = datetime.datetime.utcnow()
        db.commit()
        return {"ok": True}
    finally:
        db.close()


@app.post("/api/honeypot/session/{token}/ai-reply")
async def generate_ai_reply(token: str):
    """
    Generate the next AI honeypot reply for an ongoing session.
    Fetches the full conversation history and original scam message,
    then asks the AI to craft the best next reply to keep the scammer engaged.
    """
    db = SessionLocal()
    try:
        session = db.query(HoneypotSession).filter(HoneypotSession.session_token == token).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        messages = (
            db.query(HoneypotMessage)
            .filter(HoneypotMessage.session_token == token)
            .order_by(HoneypotMessage.timestamp.asc())
            .all()
        )

        conversation = [
            {"sender": m.sender, "content": m.content}
            for m in messages
        ]

        result = generate_honeypot_continuation(
            original_scam=session.original_message or "",
            conversation=conversation,
            scam_type=session.scam_type or "Unknown"
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# ─── Helpers ──────────────────────────────────────────────────────────────────
def _save_log(db, message: str, result: dict) -> Optional[int]:
    try:
        new_log = MessageLog(
            original_message=message,
            detected_language=result.get("language", "Unknown"),
            comprehend_language=result.get("comprehend_language"),
            risk_score=result.get("risk_score"),
            ai_base_score=result.get("ai_base_score"),
            rule_boost=result.get("rule_boost"),
            scam_type=result.get("scam_type"),
            psychological_trick=result.get("psychological_trick"),
            model_used=result.get("model_used"),
            confidence=result.get("confidence")
        )
        db.add(new_log)
        db.commit()
        db.refresh(new_log)
        return new_log.id
    except Exception as e:
        print(f"[DB] Failed to save log: {e}")
        db.rollback()
        return None


def _create_honeypot_session(db, scan_log_id, scam_type, risk_score, source,
                               original_message, ai_honeypot_reply) -> Optional[str]:
    """Create a HoneypotSession and seed it with the AI reply as the first message."""
    try:
        token = str(uuid.uuid4())
        session = HoneypotSession(
            session_token=token,
            scan_log_id=scan_log_id,
            scam_type=scam_type,
            risk_score=risk_score,
            source=source,
            original_message=original_message,
            ai_honeypot_reply=ai_honeypot_reply,
        )
        db.add(session)
        db.flush()  # get session ID without committing

        # Seed the chat with the AI-generated honeypot reply as first "user" message
        first_msg = HoneypotMessage(
            session_token=token,
            sender="user",
            content=ai_honeypot_reply,
        )
        db.add(first_msg)
        db.commit()
        print(f"[Honeypot] ✅ Session created: {token} (risk={risk_score}, type={scam_type})")
        return token
    except Exception as e:
        print(f"[Honeypot] Failed to create session: {e}")
        db.rollback()
        return None
