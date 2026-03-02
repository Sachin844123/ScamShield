import os
import json
from typing import Dict, Any
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

# Initialize Groq client
# Using the provided key as fallback for immediate testing
api_key = os.getenv('GROQ_API_KEY')
groq_client = Groq(api_key=api_key)

def analyze_message_with_llm(message: str) -> Dict[str, Any]:
    """
    Analyzes a message using Groq's fast Llama 3 models.
    Enforces strict JSON parsing, supports multilingual inputs (Hindi, Hinglish, regional).
    """
    # Llama 3.3 70B is excellent for reasoning and structured JSON
    model_id = "llama-3.3-70b-versatile"
    
    prompt = f"""
    You are an expert scam detection and fraud prevention AI built for the Indian demographic ("AI for Bharat").
    Analyze the following message and determine if it's a scam.
    
    CRITICAL CAPABILITIES:
    1. UNDERSTAND ANY LANGUAGE: The message may be in English, Hindi, Hinglish, Marathi, Bengali, Tamil, Gujarati, or any mix of these.
    2. DETECT PSYCHOLOGICAL MANIPULATION: Explicitly detect if the message uses tactics like: "Urgency", "Authority pressure", "Fear-based threats", "Reward manipulation", "Scarcity", or "Impersonation".
    3. LOCALIZE THE RESPONSE: The "explanation" and "recommended_action" MUST be written in the SAME language/dialect in which the user sent the message (e.g., if the user sends Hinglish, respond in Hinglish).
    
    Return STRICTLY valid JSON with the following schema, and no other text or explanation:
    {{
      "language": "string (e.g., Hindi, Hinglish, Marathi, English)",
      "risk_score": "integer (0 to 100)",
      "scam_type": "string (e.g., Electricity Extortion, Investment, Phishing, None)",
      "psychological_trick": "string (e.g., Fear + Urgency, Reward Manipulation, None)",
      "explanation": "string (A detailed yet simple explanation of why this is or isn't a scam, highlighting the psychological trick used. MUST be in the input language.)",
      "recommended_action": "string (What the user should do next, e.g., Do not click. Report to 1930. MUST be in the input language.)",
      "honeypot_reply": "string (A safe, neutral, AI-generated reply the user can send back to the scammer to verify their identity without giving away personal info. Use the input language.)"
    }}
    
    IMPORTANT CONSTRAINTS:
    - Never generate real personal or financial data.
    - Do not hallucinate bank details.
    
    Message: "{message}"
    """
    
    try:
        response = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a specialized JSON-only output AI. Always output perfectly formatted JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            model=model_id,
            temperature=0.0,
            # Groq supports json_object response format
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        return json.loads(content)
        
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse LLM response into JSON: {str(e)}. Raw Output: {content}")
    except Exception as e:
        raise RuntimeError(f"Groq API Error: {str(e)}")
