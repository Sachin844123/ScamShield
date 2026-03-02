# 🤖 ScamShield Telegram Bot Setup Guide

This guide explains how to create, configure, and launch the Telegram bot interface for the ScamShield Fraud Prevention Engine.

## Step 1: Create the Bot on Telegram
1. Open the Telegram app on your phone or desktop.
2. Search for **@BotFather** (the official bot used to create other bots) and start a chat with it.
3. Send the command `/newbot`.
4. BotFather will ask for a **Name** for your bot. (e.g., `ScamShield Bharat`).
5. Next, it will ask for a **Username**. It must end in `bot` and be unique (e.g., `ScamShield_Official_Bot`).
6. Once successful, BotFather will give you a **HTTP API Token** (it looks like a long string of random characters, e.g., `123456789:ABCDefghIJKlmnOPQRstUVwxyz`). Keep this token completely secret!

## Step 2: Configure Your Environment
Now that you have your Bot Token, you need to plug it into the ScamShield project.

1. Navigate to your project folder: `c:\Projects\AWS-Prototype\ScamShield`.
2. Open the `.env` file (if you haven't created one yet, copy `.env.example` to `.env`).
3. Find the line that says `TELEGRAM_BOT_TOKEN=`.
4. Paste your token there:
   ```ini
   TELEGRAM_BOT_TOKEN=123456789:ABCDefghIJKlmnOPQRstUVwxyz
   ```

## Step 3: Run the Backend API
The Telegram bot is "dumb"—it does not run AI analysis itself. It simply forwards messages to your FastAPI backend. **Therefore, the backend must be running first.**

In a terminal, navigate to your project and start the server:
```powershell
cd c:\Projects\AWS-Prototype\ScamShield
.\venv\Scripts\activate
uvicorn main:app --reload
```
*(Leave this terminal running!)*

## Step 4: Run the Telegram Bot
You need to run the bot script in a separate terminal window so it can "listen" for incoming messages via Telegram's polling system.

1. Open a **new** PowerShell terminal window.
2. Navigate to your project and activate the virtual environment:
   ```powershell
   cd c:\Projects\AWS-Prototype\ScamShield
   .\venv\Scripts\activate
   ```
3. Run the bot script:
   ```powershell
   python bot.py
   ```
4. You should see the message: `🤖 Bot is polling for messages...` in the console.

## Step 5: Test Your Bot
1. Go back to Telegram and search for your newly created bot's username (or click the link BotFather gave you).
2. Click **Start** or type `/start`.
3. Try pasting a phishing message into the chat (e.g., "Urgent your SBI KYC is blocked, click here to update or your account will be suspended").
4. Wait a few seconds. The bot will send your message to your local FastAPI backend, process it through Groq AI and the Rule Engine, and instantly reply with the structured Risk Score, Scam Type, and Psychological Tricks detected!
