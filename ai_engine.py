import os
import json
import boto3
from typing import Dict, Any
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

# ─── Bedrock Model Priority List ─────────────────────────────────────────────
# Ordered best → fastest. First model with access granted will be used.
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
BEDROCK_MODELS_PRIORITY = [
    "arn:aws:bedrock:us-east-1:983189016551:inference-profile/us.anthropic.claude-3-5-sonnet-20240620-v1:0", # Claude 3.5 Sonnet v1 (Exact ARN provided by user)
    "global.anthropic.claude-sonnet-4-6",           # Claude 4.6 Sonnet (Global)
    "us.anthropic.claude-sonnet-4-6",               # Claude 4.6 Sonnet (US)
    "global.anthropic.claude-sonnet-4-5-20250929-v1:0", # Claude 4.5 Sonnet (Global)
    "us.anthropic.claude-sonnet-4-5-20250929-v1:0", # Claude 4.5 Sonnet (US)
    "us.anthropic.claude-3-7-sonnet-20250219-v1:0", # Claude 3.7 Sonnet (US)
    "us.anthropic.claude-3-5-sonnet-20241022-v2:0", # Claude 3.5 Sonnet v2 (US)
    "us.anthropic.claude-3-5-sonnet-20240620-v1:0", # Claude 3.5 Sonnet v1 (US)
    "anthropic.claude-3-haiku-20240307-v1:0",       # Claude 3 Haiku — confirmed working
]
BEDROCK_MODEL_ID = BEDROCK_MODELS_PRIORITY[0]  # overridden at runtime by _get_best_model()

# ─── Groq (Llama 3.3 70B) – Fallback ─────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

# ─── Amazon Comprehend – Language Detection ───────────────────────────────────
COMPREHEND_ENABLED = bool(os.getenv("AWS_ACCESS_KEY_ID"))

# ─── Auto-discover best available Bedrock model ───────────────────────────────
_active_bedrock_model = None

def _get_best_model() -> str:
    """
    Probes each model in the priority list at startup and returns the first one
    that is accessible. Result is cached globally so we only probe once.
    """
    global _active_bedrock_model
    if _active_bedrock_model:
        return _active_bedrock_model

    if not os.getenv("AWS_ACCESS_KEY_ID"):
        return None  # No AWS creds → skip Bedrock entirely

    client = boto3.client("bedrock-runtime", region_name=AWS_REGION)
    probe_body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 4,
        "messages": [{"role": "user", "content": "Hi"}]
    })

    for model_id in BEDROCK_MODELS_PRIORITY:
        try:
            client.invoke_model(
                modelId=model_id,
                contentType="application/json",
                accept="application/json",
                body=probe_body
            )
            _active_bedrock_model = model_id
            print(f"[AI Engine] ✅ Bedrock model selected: {model_id}")
            return model_id
        except Exception:
            continue

    print("[AI Engine] ⚠️  No Bedrock model accessible. Will use Groq.")
    _active_bedrock_model = None
    return None


def _build_prompt(message: str) -> str:
    return f"""
    You are an expert scam detection and fraud prevention AI built for the Indian demographic.
    Analyze the following message and determine if it's a scam.

    CRITICAL CAPABILITIES:
    1. UNDERSTAND ANY LANGUAGE: The message may be in English, Hindi, Hinglish, Marathi, Bengali, Tamil, Gujarati, or any mix.
    2. DETECT PSYCHOLOGICAL MANIPULATION: Explicitly detect tactics like: "Urgency", "Authority pressure",
       "Fear-based threats", "Reward manipulation", "Scarcity", or "Impersonation".
    3. LOCALIZE THE RESPONSE: "explanation" and "recommended_action" MUST be in the SAME language as the user's input.

    Return STRICTLY valid JSON with this schema, no other text:
    {{
      "language": "string (e.g., Hindi, Hinglish, Marathi, English)",
      "risk_score": "integer (0 to 100)",
      "scam_type": "string (e.g., Electricity Extortion, Investment, Phishing, None)",
      "psychological_trick": "string (e.g., Fear + Urgency, Reward Manipulation, None)",
      "explanation": "string (detailed explanation of why this is/isn't a scam, MUST be in the input language)",
      "recommended_action": "string (what the user should do next, MUST be in the input language)",
      "honeypot_reply": "string (a safe, neutral reply the user can send to verify the scammer's identity, use input language)",
      "confidence": "string (High / Medium / Low – your confidence in this assessment)"
    }}

    CONSTRAINTS:
    - Never generate real personal or financial data.
    - Do not hallucinate bank details.
    - Risk score 0-30 = likely safe. 31-70 = suspicious. 71-100 = confirmed scam.

    Message: "{message}"
    """


def _detect_language_comprehend(message: str) -> str:
    """Uses Amazon Comprehend to detect the dominant language as a cross-check."""
    try:
        comprehend = boto3.client("comprehend", region_name=AWS_REGION)
        response = comprehend.detect_dominant_language(Text=message[:1000])
        languages = response.get("Languages", [])
        if languages:
            lang_code = languages[0].get("LanguageCode", "")
            lang_map = {
                "hi": "Hindi", "en": "English", "mr": "Marathi",
                "bn": "Bengali", "ta": "Tamil", "te": "Telugu",
                "gu": "Gujarati", "pa": "Punjabi", "ur": "Urdu"
            }
            return lang_map.get(lang_code, lang_code.upper())
    except Exception as e:
        print(f"[Comprehend] Language detection skipped: {e}")
    return None


def _analyze_with_bedrock(message: str) -> Dict[str, Any]:
    """Primary LLM: AWS Bedrock — auto-selects best available Claude model."""
    model_id = _get_best_model()
    if not model_id:
        raise RuntimeError("No Bedrock model accessible.")

    client = boto3.client("bedrock-runtime", region_name=AWS_REGION)

    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
        "temperature": 0.0,
        "system": "You are a specialized JSON-only output AI for scam detection. Always output perfectly formatted JSON and nothing else.",
        "messages": [
            {"role": "user", "content": _build_prompt(message)}
        ]
    })

    response = client.invoke_model(
        modelId=BEDROCK_MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=body
    )

    result_body = json.loads(response["body"].read())
    content = result_body["content"][0]["text"]
    parsed = json.loads(content)
    parsed["model_used"] = f"AWS Bedrock ({model_id.split('.')[1].replace('-v1:0','').replace('-v2:0','')})"
    return parsed


def _analyze_with_groq(message: str) -> Dict[str, Any]:
    """Fallback LLM: Groq Llama 3.3 70B."""
    if not groq_client:
        raise RuntimeError("Groq client not configured. Set GROQ_API_KEY in .env")

    response = groq_client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": "You are a specialized JSON-only output AI for scam detection. Always output perfectly formatted JSON."
            },
            {
                "role": "user",
                "content": _build_prompt(message)
            }
        ],
        model="llama-3.3-70b-versatile",
        temperature=0.0,
        response_format={"type": "json_object"}
    )

    content = response.choices[0].message.content
    parsed = json.loads(content)
    parsed["model_used"] = "Groq (Llama 3.3 70B) [Fallback]"
    return parsed


def analyze_message_with_llm(message: str) -> Dict[str, Any]:
    """
    Main entry point. Tries Bedrock Claude 3.5 Sonnet first, falls back to Groq.
    Also enriches the language field using Amazon Comprehend when available.
    """
    result = None
    errors = []

    # 1. Try AWS Bedrock (primary)
    if os.getenv("AWS_ACCESS_KEY_ID"):
        try:
            result = _analyze_with_bedrock(message)
            print(f"[AI Engine] ✅ Bedrock Claude 3.5 Sonnet used.")
        except Exception as e:
            errors.append(f"Bedrock error: {e}")
            print(f"[AI Engine] ⚠️ Bedrock failed, falling back to Groq: {e}")

    # 2. Fallback to Groq
    if result is None:
        try:
            result = _analyze_with_groq(message)
            print(f"[AI Engine] ✅ Groq Llama 3.3 70B used (fallback).")
        except Exception as e:
            errors.append(f"Groq error: {e}")
            raise RuntimeError(
                f"All AI engines failed. Errors: {'; '.join(errors)}"
            )

    # 3. Amazon Comprehend language cross-check (optional enrichment)
    if COMPREHEND_ENABLED:
        comprehend_lang = _detect_language_comprehend(message)
        if comprehend_lang:
            result["comprehend_language"] = comprehend_lang
            # If LLM reported English but Comprehend says Hindi → prefer Comprehend
            if result.get("language", "").lower() == "english" and comprehend_lang != "English":
                result["language"] = comprehend_lang

    return result


# ─── Honeypot Chat Continuation ───────────────────────────────────────────────

def _build_continuation_prompt(original_scam: str, conversation: list, scam_type: str) -> str:
    """Build prompt for generating the next honeypot reply in an ongoing conversation."""
    convo_text = ""
    for msg in conversation:
        role = "YOU (victim/bait)" if msg["sender"] == "user" else "SCAMMER"
        convo_text += f"\n[{role}]: {msg['content']}"

    return f"""
You are an expert honeypot agent helping trap an online scammer to expose their methods.
Your goal: generate the NEXT realistic reply the victim should send to keep the scammer engaged, extract more information (names, bank details, methods, partners), and waste their time.

ORIGINAL SCAM MESSAGE THAT STARTED THIS:
"{original_scam}"

SCAM TYPE: {scam_type or 'Unknown'}

CONVERSATION SO FAR:
{convo_text}

YOUR TASK:
Generate the next message the VICTIM should send to the scammer. The reply should:
1. Sound genuinely interested and slightly naive — like a real victim who is almost convinced
2. Ask for one specific piece of clarifying information (e.g., their name, company, account details, how to transfer, proof of legitimacy)
3. Create mild urgency or hesitation that keeps the scammer responding
4. NEVER give real financial/personal data — use vague or fictional placeholders if needed
5. Match the language and tone of the conversation (Hindi/Hinglish/English etc.)
6. Be short and natural — 1 to 3 sentences max

Also provide a brief "strategy note" explaining why this reply will work to extract more info.

Return STRICTLY valid JSON only — no other text:
{{
  "next_reply": "string — the message the victim (honeypot agent) should send",
  "strategy_note": "string — 1-sentence explanation of why this will work",
  "goal": "string — what information this reply is trying to extract"
}}
"""


def generate_honeypot_continuation(
    original_scam: str,
    conversation: list,
    scam_type: str = "Unknown"
) -> Dict[str, Any]:
    """
    Generate the next AI honeypot reply based on the conversation context.
    Uses Bedrock first, falls back to Groq.

    Args:
        original_scam: The initial scam message that started the session
        conversation: List of {"sender": "user"|"scammer", "content": str}
        scam_type: The detected scam category

    Returns:
        dict with next_reply, strategy_note, goal, model_used
    """
    prompt = _build_continuation_prompt(original_scam, conversation, scam_type)
    result = None
    errors = []

    # 1. Try Bedrock
    if os.getenv("AWS_ACCESS_KEY_ID"):
        try:
            model_id = _get_best_model()
            if model_id:
                client = boto3.client("bedrock-runtime", region_name=AWS_REGION)
                body = json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 512,
                    "temperature": 0.7,
                    "system": "You are a specialized JSON-only honeypot agent AI. Output valid JSON only.",
                    "messages": [{"role": "user", "content": prompt}]
                })
                response = client.invoke_model(
                    modelId=model_id,
                    contentType="application/json",
                    accept="application/json",
                    body=body
                )
                content = json.loads(response["body"].read())["content"][0]["text"]
                result = json.loads(content)
                result["model_used"] = f"AWS Bedrock ({model_id.split('.')[-1][:20]})"
        except Exception as e:
            errors.append(f"Bedrock: {e}")

    # 2. Fallback to Groq
    if result is None:
        try:
            if not groq_client:
                raise RuntimeError("Groq client not configured.")
            response = groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a JSON-only honeypot agent AI. Output valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                model="llama-3.3-70b-versatile",
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            result = json.loads(response.choices[0].message.content)
            result["model_used"] = "Groq (Llama 3.3 70B) [Fallback]"
        except Exception as e:
            errors.append(f"Groq: {e}")
            raise RuntimeError(f"All AI engines failed for continuation: {'; '.join(errors)}")

    return result
