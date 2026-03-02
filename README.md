# 🛡️ ScamShield - AI for Bharat Fraud Prevention Engine

ScamShield is a hybrid AI-powered fraud analysis engine deployed on AWS, accessible via Telegram and Web, designed to prevent digital fraud in India by detecting, explaining, scoring, and guiding users about suspicious messages in real time using multilingual intelligence and Indian context-aware rule enhancement.

## 🏗️ 5-Layer System Architecture

1. **User Interface Layer**: Telegram Bot & Web UI offering real time fraud prevention for users. Frictionless access via Telegram; structured analysis via Web.
2. **API Layer (`main.py`)**: Central FastAPI backend handling language detection, routing, and data flow.
3. **AI Analysis Layer (`ai_engine.py`)**: AWS Bedrock (Claude 3.5 Sonnet) providing semantic intelligence, detecting psychological manipulation (e.g., Fear + Urgency), and providing multilingual explanations (Hindi, Hinglish, Marathi, Bengali, Tamil, etc.).
4. **Risk & Decision Layer (`risk_engine.py`)**: Hybrid rule-based intelligence adding deterministic boosts for Indian-specific scams (KBC Lottery, Mahadiscom, SBI KYC, UPI pattern recognition) and obfuscated urgency text (e.g., "0 T P").
5. **Storage Layer (`database.py`)**: SQLite automated tracking recording detected language, psychological manipulation tactics, and final risk score to build a fraud intelligence dataset over time.

## ⚙️ Setup Instructions (Local)

1. Clone the repository and navigate to the project root.
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy the `.env.example` file to `.env` and fill in your details:
   ```bash
   cp .env.example .env
   ```
5. Run the web server:
   ```bash
   uvicorn main:app --reload
   ```

## ☁️ AWS Bedrock Setup Guide

1. Log in to your AWS Console and navigate to **Amazon Bedrock**.
2. Go to **Model Access** on the left menu.
3. Request access to **Anthropic Claude 3 Sonnet** (`anthropic.claude-3-sonnet-20240229-v1:0`).
4. Create an IAM User with programmatic access and attach the `AmazonBedrockFullAccess` policy.
5. Note the Access Key ID and Secret Access Key, and place them in your `.env` file!

## 🚀 EC2 Deployment Steps

To deploy ScamShield to an AWS EC2 instance publicly:

1. **Launch EC2**:
   - Go to EC2 Dashboard and click "Launch Instances".
   - Select **Ubuntu Server 22.04 LTS**.
   - Choose `t2.micro` or `t3.micro`.
   - Under Network settings, allow SSH (Port 22) and HTTP (Port 8000).
   - Launch and download the key pair.

2. **Connect and Install Dependencies**:
   ```bash
   ssh -i your-key.pem ubuntu@<your-ec2-public-ip>
   sudo apt update
   sudo apt install python3-pip python3-venv git -y
   ```

3. **Clone and Setup Environment**:
   ```bash
   git clone <your-repo-url> scamshield
   cd scamshield
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   nano .env # Add your AWS keys and Telegram Bot Token here
   ```

4. **Run Uvicorn (Web API)**:
   ```bash
   # Run in background via nohup
   nohup uvicorn main:app --host 0.0.0.0 --port 8000 &
   ```
   Now access the Web UI at: `http://<your-ec2-public-ip>:8000`

5. **Run Telegram Bot**:
   ```bash
   nohup python bot.py &
   ```

## 🧪 Demo Instructions (AI for Bharat Focus)

Try testing the system using the Web UI or Telegram Bot with the following Indian context-specific messages:

**🔴 Hinglish KBC Test (Obfuscated + Reward Manipulation):**
> "Congratulations! Aap KBC lottery jeet gaye ho. Claim karne ke liye turant apna account details aur O T P share karein."

**🔴 Hindi Electricity Scam (Fear + Urgency):**
> "Priye grahak, aapka bijli ka connection Mahadiscom dwara aaj raat 9 baje kaat diya jayega. Pichla bill update karne ke liye is link par click karein."

**🔴 UPI Fraud Impersonation:**
> "Your tax refund of Rs 15000 is pending. Please verify your UPI pin on the link fast to receive the transfer."

**🟢 Baseline Safe Message (Hinglish):**
> "Bhai, main office pahunch gaya. Shaam ko milenge event ke baad."
