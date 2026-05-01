#!/bin/bash
echo "Setting up GPX Animation Generator..."

pip install -r requirements.txt
playwright install chromium

echo "Setup complete!"
echo "Run with: streamlit run app.py"
