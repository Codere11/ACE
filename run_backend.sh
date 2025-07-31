#!/bin/bash

# --- CONFIGURATION ---
VENV_DIR="venv"
RASA_PORT=5005
FASTAPI_PORT=8000
FASTAPI_MODULE="main:app"

echo "🟢 Starting Omsoft ACE backend..."

# --- CREATE AND ACTIVATE VENV ---
if [ ! -d "$VENV_DIR" ]; then
  echo "🔧 Creating virtual environment..."
  python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
echo "✅ Virtual environment activated"

# --- START RASA IN BACKGROUND ---
echo "🚀 Starting Rasa server on port $RASA_PORT..."
rasa run --enable-api --port $RASA_PORT --cors "*" > rasa.log 2>&1 &

RASA_PID=$!
echo "🧠 Rasa PID: $RASA_PID"

# --- WAIT FOR RASA TO BE READY ---
echo "⏳ Waiting for Rasa to start..."
until curl -s http://localhost:$RASA_PORT/ | grep -q "Hello from Rasa"; do
  sleep 1
done
echo "✅ Rasa is running"

# --- START FASTAPI ---
echo "⚙️ Starting FastAPI on port $FASTAPI_PORT..."
uvicorn "$FASTAPI_MODULE" --port $FASTAPI_PORT --reload

# --- CLEANUP ---
echo "🛑 Stopping Rasa (PID: $RASA_PID)"
kill $RASA_PID
