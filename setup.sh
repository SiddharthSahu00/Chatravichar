#!/bin/bash
# Setup script for NoteForge

echo "Installing NoteForge dependencies..."

if command -v uv &> /dev/null; then
    uv sync
else
    pip install -r requirements.txt
fi

echo "Setup complete!"
echo "Copy .env.example to .env and add your GROQ API key"
echo "Run: streamlit run app.py"