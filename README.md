<div align="center">

# 🛡️ ScamShield
### *AI-Powered Scam Detection for Bharat*

**Built for the AWS Hackathon 2026**

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![AWS Bedrock](https://img.shields.io/badge/AWS_Bedrock-Claude_3.5_Sonnet-FF9900?style=flat&logo=amazonaws&logoColor=white)](https://aws.amazon.com/bedrock/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green?style=flat)](LICENSE)

> India's first **multilingual, hybrid AI scam detection system** that understands Hindi, Hinglish, Marathi, Bengali, Tamil, and more — powered by AWS Bedrock, Amazon Comprehend, and a rule-based engine tuned for the Indian threat landscape.

[🌐 Web App](#-quick-start) · [🤖 Telegram Bot](https://t.me/ScamShield_Official_Bot) · [☁️ AWS Deploy](#%EF%B8%8F-aws-deployment) · [📖 Upgrade Roadmap](upgradetion.md)

</div>

---

## 📌 The Problem

Over **₹1,776 crore** was lost to cyber fraud in India in 2023 alone. Scammers exploit:
- **Language barriers** — most Indians communicate in regional languages, not English
- **Psychological manipulation** — Fear, Urgency, Authority, Reward tactics
- **Local context** — KBC lotteries, Mahadiscom bills, SBI KYC, UPI phishing

Existing tools are English-only, rule-only, or too slow. **ScamShield is different.**

---

## ✨ Key Features

| Feature | Description |
|---|---|
| 🧠 **Dual AI Engine** | AWS Bedrock Claude 3.5 Sonnet (primary) + Groq Llama 3.3 70B (fallback) |
| 🌍 **Multilingual** | Detects and responds in Hindi, Hinglish, Marathi, Bengali, Tamil, Gujarati, English |
| 🔬 **Amazon Comprehend** | Language cross-verification and PII intent detection |
| 📊 **Hybrid Scoring** | AI semantic score + Indian-specific rule engine (KYC, UPI, Lottery, Extortion) |
| 🔗 **URL Intelligence** | urlscan.io screenshot capture + IP / SSL / domain reputation |
| 🧠 **Psychological Analysis** | Detects: Fear, Urgency, Authority, Reward, Impersonation, Scarcity tactics |
| 🪤 **Honeypot Generator** | AI-generated safe replies to trick scammers into revealing identity |
| 🤖 **Telegram Bot** | Full conversation interface with scan history |
| 🗄️ **AWS RDS** | PostgreSQL on Amazon RDS (SQLite fallback for local dev) |
| ☁️ **AWS Elastic Beanstalk** | One-command deployment, auto-scaling |

---

## 🏗️ System Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      USER INTERFACES                         │
│         Web UI (FastAPI/Jinja2)  ·  Telegram Bot             │
└───────────────────────┬──────────────────────────────────────┘
                        │  POST /api/analyze
                        ▼
┌──────────────────────────────────────────────────────────────┐
│                   FastAPI Backend (main.py)                   │
│   /health · /api/analyze · /api/stats · /analyze (web form) │
└────┬──────────────────┬─────────────────────┬───────────────┘
     │                  │                     │
     ▼                  ▼                     ▼
┌─────────┐    ┌─────────────────┐    ┌──────────────┐
│URLScan  │    │  AI Engine      │    │  Risk Engine │
│Service  │    │  (ai_engine.py) │    │(risk_engine) │
│         │    │                 │    │              │
│urlscan  │    │ ① AWS Bedrock   │    │ Rule boosts: │
│.io API  │    │   Claude 3.5    │    │ • OTP/KYC    │
│         │    │   Sonnet        │    │ • UPI/GPay   │
│Screenshot│   │                 │    │ • Lottery    │
│ Capture │    │ ② Groq Fallback │    │ • Threats    │
└────┬────┘    │   Llama 3.3 70B │    │ • Shortened  │
     │         │                 │    │   URLs       │
     │         │ ③ Comprehend    │    └──────┬───────┘
     │         │   Language Check│           │
     │         └────────┬────────┘           │
     │                  │                    │
     └──────────────────┴────────────────────┘
                        │
                        ▼ Hybrid Score (capped at 100)
┌──────────────────────────────────────────────────────────────┐
│              Amazon RDS PostgreSQL  (database.py)            │
│    Stores: message · language · risk_score · scam_type       │
│    model_used · confidence · psychological_trick · timestamp │
└──────────────────────────────────────────────────────────────┘
```

---

## 🔧 Tech Stack

| Layer | Technology |
|---|---|
| **AI Primary** | AWS Bedrock — Claude 3.5 Sonnet |
| **AI Fallback** | Groq — Llama 3.3 70B Versatile |
| **Language Detection** | Amazon Comprehend |
| **URL Analysis** | urlscan.io API |
| **Backend** | FastAPI + Uvicorn |
| **Database** | Amazon RDS PostgreSQL / SQLite (local) |
| **Bot** | python-telegram-bot |
| **Hosting** | AWS Elastic Beanstalk (t3.micro) |
| **Secrets** | AWS Secrets Manager |
| **Container** | Docker |

---

## ⚡ Quick Start (Local Development)

### Prerequisites
- Python 3.11+
- A [Groq API key](https://console.groq.com) (free)
- A [Telegram Bot Token](https://t.me/BotFather)
- AWS credentials (for Bedrock + Comprehend — optional, Groq is the fallback)

### 1. Clone & Install

```bash
git clone https://github.com/your-username/scamshield.git
cd scamshield

python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac

pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Open `.env` and fill in your keys:

```env
# Required
GROQ_API_KEY=your_groq_api_key
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
URLSCAN_API_KEY=your_urlscan_api_key

# Optional (activates Bedrock as primary AI)
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
AWS_REGION=us-east-1
```

### 3. Run

```bash
# Terminal 1: Start the FastAPI web server
uvicorn main:app --reload
# → Open http://localhost:8000

# Terminal 2: Start the Telegram Bot
python bot.py
```

---

## 📡 API Reference

### `POST /api/analyze`
Analyze a message or URL for scam content.

**Request:**
```json
{ "message": "URGENT: Your SBI KYC is expired. Click http://sbi-kyc.xyz now!" }
```

**Response:**
```json
{
  "language": "Hinglish",
  "risk_score": 95,
  "ai_base_score": 70,
  "rule_boost": 25,
  "scam_type": "KYC Phishing",
  "psychological_trick": "Fear + Urgency",
  "explanation": "Yeh message ek phishing scam hai...",
  "recommended_action": "Is link par bilkul click na karein...",
  "honeypot_reply": "Please send the official request to my registered bank email.",
  "confidence": "High",
  "model_used": "AWS Bedrock (Claude 3.5 Sonnet)",
  "urlscan_details": { "malicious": true, "screenshot_url": "https://..." }
}
```

### `GET /health`
Returns service health status (used by Elastic Beanstalk).

### `GET /api/stats`
Returns live aggregate statistics.
```json
{
  "total_scans": 1243,
  "high_risk_scans": 876,
  "detection_rate_pct": 70.5,
  "avg_risk_score": 64.2,
  "top_scam_type": "KYC Phishing"
}
```

---

## 🧪 Test Messages

Copy and paste these into the Web UI or Telegram Bot:

**🔴 High Risk — Hinglish KBC Lottery Scam:**
```
Congratulations! Aap KBC lottery jeet gaye ho. Claim karne ke liye turant apna account details aur O T P share karein. Offer sirf aaj valid hai!
```

**🔴 High Risk — Hindi Electricity Extortion:**
```
Priye grahak, aapka bijli ka connection Mahadiscom dwara aaj raat 9 baje kaat diya jayega. Pichla bill update karne ke liye is link par click karein: http://mahadiscom-bill.xyz
```

**🔴 High Risk — UPI Phishing:**
```
Your tax refund of Rs 15000 is pending. Please verify your UPI pin on the link fast to receive the transfer immediately.
```

**🟢 Safe — Casual Hinglish:**
```
Bhai, main office pahunch gaya. Shaam ko milenge event ke baad. Koi baat nahi agar late ho.
```

---

## ☁️ AWS Deployment

> **Full step-by-step guide → [`aws_setup.md`](aws_setup.md)**

### Quick Deploy Summary

```bash
# Install EB CLI
pip install awsebcli

# Configure AWS credentials
aws configure

# Initialize & deploy
eb init scamshield --platform python-3.11 --region us-east-1
eb create scamshield-prod --instance-type t3.micro

# Set environment variables
eb setenv \
  GROQ_API_KEY=... \
  TELEGRAM_BOT_TOKEN=... \
  URLSCAN_API_KEY=... \
  DATABASE_URL="postgresql://user:pass@rds-endpoint:5432/scamshield" \
  AWS_REGION=us-east-1

eb deploy
eb open
```

### AWS Services Used

| Service | Purpose | Est. Cost/mo |
|---|---|---|
| **Elastic Beanstalk** (t3.micro) | FastAPI hosting | ~$8 |
| **Amazon RDS** (db.t3.micro) | PostgreSQL database | ~$13 |
| **AWS Bedrock** (Claude 3.5 Sonnet) | Primary AI model | ~$3–8 |
| **Amazon Comprehend** | Language detection | ~$1 |
| **Secrets Manager** | Secure key storage | ~$0.40 |
| | **Total** | **~$28–35** |

---

## 📁 Project Structure

```
ScamShield/
├── main.py               # FastAPI app — all routes + business logic
├── ai_engine.py          # Bedrock Claude 3.5 Sonnet + Groq fallback + Comprehend
├── risk_engine.py        # Indian-specific rule-based scoring engine
├── database.py           # SQLAlchemy models — RDS/SQLite aware
├── urlscan_service.py    # URL scanning + screenshot extraction
├── bot.py                # Telegram bot (conversation handler)
├── templates/
│   └── index.html        # Web UI — live stats, dark theme, AWS branding
├── Dockerfile            # Container for AWS / local Docker
├── Procfile              # Elastic Beanstalk startup command
├── .ebextensions/
│   └── options.config    # EB health check + Python config
├── requirements.txt      # Python dependencies
├── .env.example          # Environment variable template
├── aws_setup.md          # Full AWS deployment guide (11 steps)
└── upgradetion.md        # Future upgrade roadmap
```

---

## 🔒 Security

- **No secrets in code** — all credentials via `.env` / AWS Secrets Manager
- **Secrets Manager** stores production keys on AWS (never in `.env` on server)
- **VPC recommended** — RDS in private subnet for production
- **Rate limiting** — planned via `slowapi` (see [upgrade roadmap](upgradetion.md))

---

## 🛣️ Roadmap

See the full **[Upgrade Roadmap](upgradetion.md)** for 25+ planned features. Highlights:

- [ ] Amazon Rekognition — screenshot phishing image analysis
- [ ] Amazon Comprehend PII — auto-flag Aadhaar/PAN requests
- [ ] WhatsApp Business API integration
- [ ] AWS SQS + Lambda — async non-blocking URL scans
- [ ] Live India scam heatmap
- [ ] Voice call analysis via Amazon Transcribe + Connect

---

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/rekognition-scan`
3. Commit your changes: `git commit -m "feat: add rekognition screenshot analysis"`
4. Push and open a Pull Request

---

## 📄 License

MIT © 2026 ScamShield Team. Built with ❤️ for Bharat.

---

<div align="center">

**If ScamShield helped you, please ⭐ star the repo!**

[Telegram Bot](https://t.me/ScamShield_Official_Bot) · [AWS Hackathon 2026](https://aws.amazon.com/events/hackathons/)

</div>
