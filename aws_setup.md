---

## 📋 What We're Building on AWS

```
[Your Users / Telegram Bot]
        │
        ▼
[Elastic Beanstalk] ← Both FastAPI (main.py) AND your Bot (bot.py) run simultaneously here!
        │
        ├──► [Amazon RDS PostgreSQL]  ← Scalable database 
        ├──► [AWS Bedrock - Claude 3.5 Sonnet] ← Advanced Scam Detection
        ├──► [Amazon Comprehend] ← Language detection
        └──► [AWS Secrets Manager] ← API Keys stored securely
```

---

## STEP 1: Create Your AWS Account & Get Free Credit

1. Go to [https://aws.amazon.com](https://aws.amazon.com) → click **"Create an AWS Account"**
2. Enter email, set a password, choose account name: `ScamShield`
3. Enter a credit card (required for verification — you won't be charged if within Free Tier)
4. Choose **Basic Support** (Free)
5. **Apply your $100 credit**:
   - Go to: https://console.aws.amazon.com/billing/
   - Click **"Credits"** in the left sidebar
   - Enter your promotional code → Apply

---

## STEP 2: Set Up IAM User (Never Use Root Account)

1. Open **AWS Console** → search "IAM" → click **IAM**
2. Click **Users** → **Add users**
3. Username: `scamshield-admin`
4. Select: **"Access key - Programmatic access"** ✅
5. Permissions: **Attach policies directly** → select:
   - `AdministratorAccess` (for now; restrict later in production)
6. Click through → **Download CSV** with your keys → SAVE THIS FILE! You won't see it again.
7. The CSV contains:
   - `AWS_ACCESS_KEY_ID` — looks like: `AKIA...`
   - `AWS_SECRET_ACCESS_KEY` — long random string

Put these in your `.env` file:
```env
AWS_ACCESS_KEY_ID=YOUR_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY=YOUR_SECRET_ACCESS_KEY
AWS_REGION=YOUR_REGION
```

---

## STEP 3: Set a Budget Alert (Protect Your $100 Credit)

> Do this FIRST before anything else so you don't accidentally overspend.

1. AWS Console → search "Billing" → **Budgets**
2. Click **Create a budget**
3. Choose: **Cost budget** → Next
4. Name: `ScamShield-Budget`
5. Budgeted amount: `$90` (10% safety margin)
6. Under **Alert thresholds**:
   - 80% of budgeted = email alert
   - 100% of budgeted = email alert
7. Enter YOUR email address
8. Click **Create budget**

---

## STEP 4: Create RDS PostgreSQL Database

> **Cost**: ~$13/month for db.t3.micro (cheapest option)

1. AWS Console → search "RDS" → **RDS**
2. Click **Create database**
3. Choose:
   - **Standard Create**
   - Engine: **PostgreSQL**
   - Version: **16.x** (latest)
   - Template: **Free tier** ✅ (if eligible) or **Dev/Test**
4. Settings:
   - DB instance identifier: `scamshield-db`
   - Master username: `scamshield_admin`
   - Master password: create a strong password (save it!)
5. Instance configuration:
   - DB instance class: `db.t3.micro` (cheapest)
6. Storage: `20 GB gp2` (minimum)
7. Connectivity:
   - VPC: **Default VPC**
   - Public access: **Yes** (for initial setup; lock down later)
   - VPC security group: **Create new** → name it `scamshield-db-sg`
8. Click **Create database** → wait ~5 minutes

9. **Get your connection string**:
   - Click your new DB → copy the **Endpoint** (looks like: `scamshield-db.abc123.us-east-1.rds.amazonaws.com`)
   - Your DATABASE_URL will be:
     ```
     postgresql://scamshield_admin:YOUR_PASSWORD@scamshield-db.abc123.us-east-1.rds.amazonaws.com:5432/scamshield
     ```

10. **Create the database name** (one-time):
    - Install psql OR use the RDS query editor
    - Run: `CREATE DATABASE scamshield;`

---

## STEP 5: Enable AWS Bedrock Claude 3.5 Sonnet

> **Cost**: ~$3 per 1M input tokens — powerful reasoning for accurate scam detection

1. AWS Console → search "Bedrock" → **Amazon Bedrock**
2. In the left menu → **Model access**
3. Find **"Claude 3.5 Sonnet"** by Anthropic → click **"Request access"**
4. Fill out the short form (how you plan to use it: "Scam detection for Indian users")
5. Usually approved within **5-10 minutes**
6. ✅ Once approved, you'll see a green "Access granted" next to Claude 3.5 Sonnet

---

## STEP 6: Store API Keys in AWS Secrets Manager

> **Cost**: $0.40/month — much safer than putting keys in .env on a server

1. AWS Console → search "Secrets Manager" → **AWS Secrets Manager**
2. Click **Store a new secret**
3. Choose: **Other type of secret**
4. Add key-value pairs:
   ```
   GROQ_API_KEY          → your-groq-api-key
   TELEGRAM_BOT_TOKEN    → your-telegram-bot-token
   URLSCAN_API_KEY       → your-urlscan-api-key
   DATABASE_URL          → postgresql://...full-connection-string...
   ```
5. Secret name: `scamshield/prod`
6. Click through → **Store**

---

## STEP 7: Prepare Your Project & Install Dependencies

On your local machine:

```bash
cd C:\Projects\AWS-Prototype\ScamShield

# Activate virtual environment
.\venv\Scripts\activate

# Install new dependencies
pip install boto3 psycopg2-binary

# Update requirements.txt
pip freeze > requirements.txt
```

Make sure your `.env` file has these values filled in (for local testing):
```env
GROQ_API_KEY=your-actual-groq-key
TELEGRAM_BOT_TOKEN=your-actual-bot-token
URLSCAN_API_KEY=your-actual-urlscan-key
AWS_ACCESS_KEY_ID=from-step-2-csv
AWS_SECRET_ACCESS_KEY=from-step-2-csv
AWS_REGION=us-east-1
DATABASE_URL=postgresql://...from-step-4...
API_URL=http://localhost:8000/api/analyze
```

---

## STEP 8: Install AWS CLI + EB CLI

```bash
# Install AWS CLI
winget install Amazon.AWSCLI

# Install Elastic Beanstalk CLI
pip install awsebcli

# Configure AWS CLI with your credentials from Step 2
aws configure
# Prompts:
#   AWS Access Key ID: [paste from CSV]
#   AWS Secret Access Key: [paste from CSV]
#   Default region name: us-east-1
#   Default output format: json
```

Verify it works:
```bash
aws sts get-caller-identity
# Should show your account ID and user ARN
```

---

## STEP 9: Deploy to Elastic Beanstalk

> **Cost**: ~$8-15/month for t3.micro instance

```bash
cd C:\Projects\AWS-Prototype\ScamShield

# Initialize EB application (run once)
eb init scamshield --platform python-3.11 --region us-east-1

# When prompted:
# - Do you want to use CodeCommit? No
# - Do you want to set up SSH? Yes (optional but recommended)

# Create the environment
eb create scamshield-prod --instance-type t3.micro

# This takes 5-8 minutes... wait for it

# Set your environment variables on EB (replaces .env on the server)
# Note: Run this as a single line in your terminal
eb setenv GROQ_API_KEY=your-groq-key TELEGRAM_BOT_TOKEN=your-token URLSCAN_API_KEY=your-key AWS_REGION=us-east-1 DATABASE_URL="postgresql://scamshield_admin:PASSWORD@endpoint:5432/scamshield"

# Deploy your app
eb deploy

# Open in browser
eb open
```

**Your app URL** will look like: `http://scamshield-prod.eba-abc123.us-east-1.elasticbeanstalk.com`

---

## STEP 10: Update Telegram Bot to Use AWS URL

Since you are deploying using Elastic Beanstalk and we've set up the `Procfile` correctly in your project, **both the website and the Telegram bot will run on the same server automatically**. 

1. Once your EB deployment is working, look up your `.elasticbeanstalk.com` URL (you can see it by running `eb status`).
2. Run this command to update the `API_URL` environment variable inside Elastic Beanstalk, so your bot knows where to reach your backend logic instead of using `localhost`:

```bash
eb setenv API_URL=http://YOUR-EB-APP-URL.us-east-1.elasticbeanstalk.com/api/analyze BASE_URL=http://YOUR-EB-APP-URL.us-east-1.elasticbeanstalk.com
```

3. Wait a minute for the environment to update. Elastic Beanstalk will internally run:
   - `web: uvicorn main:app --port 5000` (The dashboard API)
   - `bot: python bot.py` (The Telegram bot that constantly listens for messages)

That's it! Because the bot initiates connections to Telegram, it requires zero port forwarding and NO custom domain.

---

## STEP 11: Verify Everything Works

### ✅ Web Frontend Check
1. Visit your EB URL in browser
2. Paste a test scam message: *"Congratulations! Your KBC lottery win of Rs 25 lakh, claim your prize now. Click: http://kbc-prize.xyz"*
3. Should see Risk Score > 70 with detailed analysis

### ✅ Telegram Bot Check
1. Open Telegram → find your bot → send `/start`
2. Choose "Scan Message / URL"
3. Send the same scam message above
4. Should get full analysis including screenshot

### ✅ Database Check
```bash
# Check RDS has data:
aws rds-data execute-statement \
  --resource-arn "your-rds-arn" \
  --database "scamshield" \
  --sql "SELECT COUNT(*) FROM message_logs"
```

### ✅ Bedrock AI Check
```bash
python -c "
from ai_engine import analyze_message_with_llm
result = analyze_message_with_llm('Your SBI KYC is expired. Update now.')
print('Risk Score:', result.get('risk_score'))
print('Model Used:', result.get('model_used', 'not reported'))
"
```

---

## 💰 Cost Management Tips (Protect Your $100)

| Action | Monthly Saving |
|---|---|
| Stop RDS when not needed (dev only) | ~$13 |
| Use t3.micro (not t3.small) | ~$10 |
| Keep Bedrock requests < 1M tokens | ~$5 |
| Delete old EB environments | ~$8 |
| Use Free Tier for first 12 months | Varies |

**Golden rule**: If you're just developing and not having users, go to:
- RDS → Stop (stops billing for up to 7 days at a time)
- EB → Terminate environment (recreate when needed)

---

## 🛡️ Security Hardening (Do This After Basic Deployment Works)

1. **RDS Security Group**: Change public access to "No", only allow traffic from EB's security group IP
2. **HTTPS**: In EB → Load Balancer → add SSL certificate via AWS Certificate Manager (free)
3. **IAM Role**: Create a restrictive IAM role for the EB instance (not AdministratorAccess)
4. **Rotate Keys**: After testing, rotate your IAM access keys every 90 days

---

## ❓ Troubleshooting

| Problem | Fix |
|---|---|
| `eb deploy` fails | Run `eb logs` to see the error |
| `Connection refused` on RDS | Check Security Group allows port 5432 from your IP |
| Bedrock `AccessDeniedException` | Model access not granted yet (Step 5) |
| Bot says "Error analyzing message" | API_URL env var not updated to AWS URL |
| Web page shows 502 Bad Gateway | App crashed on startup. Run `eb logs` |
