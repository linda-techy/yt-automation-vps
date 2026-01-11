#!/bin/bash
#
# YouTube Automation VPS Deployment Script
# For Ubuntu/Debian servers (Hostinger VPS)
#
# Usage: chmod +x deploy.sh && ./deploy.sh
#

set -e  # Exit on error

echo "================================================"
echo "YouTube Automation - VPS Deployment"
echo "================================================"

# Update system
echo "[1/6] Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install Python 3.10+
echo "[2/6] Installing Python 3.10..."
sudo apt install -y python3.10 python3.10-venv python3-pip

# Install FFmpeg
echo "[3/6] Installing FFmpeg..."
sudo apt install -y ffmpeg

# Install ImageMagick
echo "[4/6] Installing ImageMagick..."
sudo apt install -y imagemagick

# Install Malayalam and Unicode fonts
echo "[5/6] Installing fonts..."
sudo apt install -y fonts-noto fonts-noto-extra fonts-lohit-mlym

# Fix ImageMagick policy for MoviePy (PDF/PS disabled by default)
echo "[5.5/6] Configuring ImageMagick policy..."
sudo sed -i 's/<policy domain="path" rights="none" pattern="@\*"\/>//g' /etc/ImageMagick-6/policy.xml 2>/dev/null || true
sudo sed -i 's/<policy domain="coder" rights="none" pattern="PDF" \/>//g' /etc/ImageMagick-6/policy.xml 2>/dev/null || true

# Install Python dependencies
echo "[6/6] Installing Python packages..."
pip3 install -r requirements.txt

echo ""
echo "================================================"
echo "Deployment Complete!"
echo "================================================"
echo ""
echo "NEXT STEPS:"
echo "1. Copy client_secret.json to this directory"
echo "2. Generate OAuth token: python3 -c \"from services.youtube_uploader import generate_token_headless; generate_token_headless()\""
echo "   (Or copy existing token.pickle from your local machine)"
echo "3. Create .env file with:"
echo "   OPENAI_API_KEY=your_key"
echo "   PIXABAY_API_KEY=your_key"
echo "   YOUTUBE_CLIENT_SECRET_FILE=client_secret.json"
echo "   YOUTUBE_TOKEN_FILE=token.pickle"
echo "4. Test pipeline: python3 pipeline.py"
echo ""
echo "Set up cron for daily automation:"
echo "crontab -e"
echo "0 20 * * * cd $(pwd) && python3 pipeline.py >> logs/cron.log 2>&1"
