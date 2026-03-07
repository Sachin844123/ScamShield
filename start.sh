#!/bin/bash

# Start the Telegram bot in the background
python bot.py &

# Start the FastAPI web server in the foreground
# Render automatically provides a $PORT environment variable (usually 10000)
uvicorn main:app --host 0.0.0.0 --port $PORT
