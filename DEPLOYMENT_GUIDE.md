# Production VPS Deployment Guide

**Complete step-by-step guide for deploying YouTube Automation System on Ubuntu VPS**

---

## Prerequisites

### VPS Requirements

| Spec | Minimum | Recommended |
|------|---------|-------------|
| OS | Ubuntu 20.04+ | Ubuntu 22.04 LTS |
| RAM | 2GB | 4GB+ |
| Storage | 20GB | 40GB+ SSD |
| CPU | 1 core | 2+ cores |
| Bandwidth | 1TB/month | Unlimited |

### Local Machine Requirements

- Python 3.10+ installed
- Git installed
- SSH client
- Web browser (for OAuth setup)

---

## Phase 1: Local Setup (OAuth Token Generation)

**⚠️ IMPORTANT**: OAuth token generation requires a browser, so this MUST be done on your local machine first.

### Step 1.1: Clone and Install Locally

```bash
# Clone repository
git clone <your-repo-url> yt-automation
cd yt-automation

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
```

### Step 1.2: Configure API Keys

Edit `.env` file:

```bash
# Open in your preferred editor
nano .env  # or: code .env, vim .env, etc.
```

Add your credentials:
```env
OPENAI_API_KEY=sk-your-actual-openai-key
PIXABAY_API_KEY=your-pixabay-key
YOUTUBE_CLIENT_SECRET_FILE=client_secret.json
YOUTUBE_TOKEN_FILE=token.pickle
```

### Step 1.3: Setup YouTube OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project (or select existing)
3. Enable **YouTube Data API v3**
4. Create OAuth 2.0 credentials:
   - Application type: **Desktop App**
   - Name: `YouTube Automation`
5. Download `client_secret.json` to project root

```bash
# Verify file exists
ls -la client_secret.json
```

### Step 1.4: Generate OAuth Token

```bash
python -c "from services.youtube_uploader import generate_token_headless; generate_token_headless()"
```

**Follow the prompts:**
1. Browser will open automatically
2. Login to YouTube account
3. Grant permissions
4. `token.pickle` will be created

```bash
# Verify token created
ls -la token.pickle
```

✅ **OAuth Setup Complete!** You can now deploy to VPS.

---

## Phase 2: VPS Setup

### Step 2.1: Prepare VPS

```bash
# SSH into your VPS
ssh root@your-vps-ip

# Update system
apt update && apt upgrade -y

# Install essential tools
apt install -y git curl wget build-essential python3.10 python3-pip
```

### Step 2.2: Create Application User (Security Best Practice)

```bash
# Create non-root user
adduser ytautomation

# Add to sudo group
usermod -aG sudo ytautomation

# Switch to new user
su - ytautomation
```

### Step 2.3: Upload Files to VPS

**From your LOCAL machine** (new terminal):

```bash
# Upload entire project (including token.pickle)
scp -r yt-automation/ ytautomation@your-vps-ip:/home/ytautomation/

# OR if you prefer rsync (excludes .git, __pycache__):
rsync -av --exclude='.git' --exclude='__pycache__' --exclude='videos/' \
  yt-automation/ ytautomation@your-vps-ip:/home/ytautomation/yt-automation/
```

### Step 2.4: Run Deployment Script

**Back on VPS terminal:**

```bash
cd ~/yt-automation

# Make script executable
chmod +x deploy.sh

# Run automated deployment
./deploy.sh
```

**What deploy.sh does:**
- Installs FFmpeg, ImageMagick
- Installs Python dependencies
- Installs Malayalam fonts
- Creates necessary directories
- Sets up PM2 (Node.js process manager)

---

## Phase 3: Environment Configuration

### Step 3.1: Verify .env File

```bash
cd ~/yt-automation

# Check .env exists
ls -la .env

# View (without showing secrets)
head -n 5 .env
```

If `.env` is missing, create it:

```bash
cp .env.example .env
nano .env
# Add your API keys
```

### Step 3.2: Verify OAuth Credentials

```bash
# Check both files exist
ls -la client_secret.json token.pickle

# If missing, upload from local machine:
# scp token.pickle ytautomation@your-vps-ip:/home/ytautomation/yt-automation/
# scp client_secret.json ytautomation@your-vps-ip:/home/ytautomation/yt-automation/
```

---

## Phase 4: Testing & Validation

### Step 4.1: Health Check

```bash
cd ~/yt-automation

# Run health check
python3 -c "from services.health_monitor import get_health_monitor; import json; result = get_health_monitor().run_full_health_check(); print(json.dumps(result, indent=2))"
```

**Expected output:**
```json
{
  "overall_healthy": true,
  "disk": {"healthy": true, "free_gb": 15.5},
  "memory": {"healthy": true, "available_gb": 1.8},
  "dependencies": {"healthy": true}
}
```

### Step 4.2: Test Pipeline (Dry Run)

```bash
# Run single pipeline execution
python3 pipeline.py
```

**This will:**
- Generate a topic
- Create script
- Generate TTS
- Build video
- Upload to YouTube

⏱️ **Expected duration**: 15-25 minutes

**Watch logs:**
```bash
tail -f logs/pipeline.log
```

---

## Phase 5: PM2 Daemon Setup (Production)

### Step 5.1: Install PM2

```bash
# Install Node.js (required for PM2)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Install PM2 globally
sudo npm install -g pm2
```

### Step 5.2: Start Daemon

```bash
cd ~/yt-automation

# Start daemon with PM2
pm2 start daemon.py --name "yt-automation" --interpreter python3

# View logs
pm2 logs yt-automation

# Check status
pm2 status
```

**Expected output:**
```
┌─────┬────────────────┬─────────┬─────────┬──────────┐
│ id  │ name           │ status  │ restart │ uptime   │
├─────┼────────────────┼─────────┼─────────┼──────────┤
│ 0   │ yt-automation  │ online  │ 0       │ 2m       │
└─────┴────────────────┴─────────┴─────────┴──────────┘
```

### Step 5.3: Configure Auto-Start on Reboot

```bash
# Generate startup script
pm2 startup

# Copy the command it outputs and run it (with sudo)
# Example: sudo env PATH=$PATH:/usr/bin pm2 startup systemd -u ytautomation --hp /home/ytautomation

# Save PM2 process list
pm2 save
```

### Step 5.4: Verify Auto-Start

```bash
# Test by rebooting
sudo reboot

# After reboot, SSH back and check:
pm2 status
```

---

## Phase 6: Monitoring & Maintenance

### Step 6.1: View Logs

```bash
# Real-time daemon logs
pm2 logs yt-automation

# Specific log files
tail -f logs/pipeline.log
tail -f logs/daemon.log

# View last 50 lines
pm2 logs yt-automation --lines 50
```

### Step 6.2: Check Health Status

```bash
# View health dashboard
cat channel/health_status.json | jq

# Check disk space
df -h

# Check memory
free -h
```

### Step 6.3: Monitor Quota Usage

```bash
# Install sqlite3
sudo apt install sqlite3

# View quota usage
sqlite3 channel/quota_tracker.db "SELECT * FROM quota_usage ORDER BY timestamp DESC LIMIT 10;"

# Daily summary
sqlite3 channel/quota_tracker.db "
SELECT DATE(timestamp) as date, SUM(cost) as total
FROM quota_usage
WHERE timestamp >= datetime('now', '-7 days')
GROUP BY DATE(timestamp);
"
```

### Step 6.4: Manual Pipeline Trigger

```bash
# Stop daemon
pm2 stop yt-automation

# Run single execution
python3 pipeline.py

# Restart daemon
pm2 restart yt-automation
```

---

## Phase 7: Schedule Configuration

### Step 7.1: Default Schedule

By default, daemon runs **3x per week**:
- **Monday** at 15:30 IST
- **Wednesday** at 15:30 IST
- **Friday** at 15:30 IST

This generates 3 long videos + 15 shorts per week.

### Step 7.2: Modify Schedule

Edit `daemon.py`:

```bash
nano daemon.py
```

Find lines ~79-81:
```python
schedule.every().monday.at(run_time, timezone).do(run_pipeline_job)
schedule.every().wednesday.at(run_time, timezone).do(run_pipeline_job)
schedule.every().friday.at(run_time, timezone).do(run_pipeline_job)
```

**For daily uploads**, change to:
```python
schedule.every().day.at(run_time, timezone).do(run_pipeline_job)
```

**For specific days/times:**
```python
schedule.every().tuesday.at("18:00", timezone).do(run_pipeline_job)
schedule.every().saturday.at("10:30", timezone).do(run_pipeline_job)
```

Then restart:
```bash
pm2 restart yt-automation
```

---

## Phase 8: Troubleshooting

### Issue: PM2 Not Auto-Starting After Reboot

```bash
# Re-run startup command
pm2 startup
sudo env PATH=$PATH:/usr/bin pm2 startup systemd -u ytautomation --hp /home/ytautomation

pm2 save
```

### Issue: FFmpeg Not Found

```bash
# Reinstall FFmpeg
sudo apt update
sudo apt install -y ffmpeg

# Verify
ffmpeg -version
```

### Issue: Out of Disk Space

```bash
# Check disk usage
df -h
du -sh ~/yt-automation/videos/

# Manual cleanup
python3 -c "from services.health_monitor import get_recovery_manager; get_recovery_manager().cleanup_stale_files(max_age_hours=24)"

# Or delete old videos manually
rm -rf ~/yt-automation/videos/output/*
rm -rf ~/yt-automation/videos/temp/*
```

### Issue: YouTube Quota Exceeded

```bash
# Check quota status
sqlite3 channel/quota_tracker.db "SELECT SUM(cost) FROM quota_usage WHERE timestamp >= datetime('now', '-1 day');"

# System automatically waits for reset (midnight PT)
# No action needed - pipeline will resume next day
```

### Issue: Pipeline Crashes

```bash
# Check error logs
cat channel/error_history.json | jq '.[-5:]'

# Check system logs
pm2 logs yt-automation --err

# Restart daemon
pm2 restart yt-automation
```

---

## Phase 9: Security Hardening

### Step 9.1: Firewall Configuration

```bash
# Enable UFW firewall
sudo ufw enable

# Allow SSH (IMPORTANT!)
sudo ufw allow ssh

# Allow only SSH, deny all other incoming
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Check status
sudo ufw status
```

### Step 9.2: SSH Key Authentication

```bash
# On local machine, generate SSH key
ssh-keygen -t ed25519 -C "yt-automation-vps"

# Copy to VPS
ssh-copy-id ytautomation@your-vps-ip

# On VPS, disable password authentication
sudo nano /etc/ssh/sshd_config

# Set:
PasswordAuthentication no

# Restart SSH
sudo systemctl restart sshd
```

### Step 9.3: Regular Updates

Add to crontab:
```bash
crontab -e

# Add (runs daily at 2 AM):
0 2 * * * sudo apt update && sudo apt upgrade -y
```

---

## Phase 10: Backup Strategy

### Step 10.1: Database Backups

```bash
# Create backup script
nano ~/backup.sh
```

Add:
```bash
#!/bin/bash
BACKUP_DIR=~/backups/$(date +%Y-%m-%d)
mkdir -p $BACKUP_DIR

# Backup databases
cp ~/yt-automation/channel/*.db $BACKUP_DIR/
cp ~/yt-automation/channel/*.json $BACKUP_DIR/

# Backup config
cp ~/yt-automation/.env $BACKUP_DIR/
cp ~/yt-automation/channel_config.yaml $BACKUP_DIR/

# Delete backups older than 30 days
find ~/backups/ -type d -mtime +30 -exec rm -rf {} \;

echo "Backup completed: $BACKUP_DIR"
```

```bash
chmod +x ~/backup.sh

# Test
./backup.sh

# Add to crontab (daily at 3 AM)
crontab -e
0 3 * * * /home/ytautomation/backup.sh
```

---

## Summary Checklist

- [ ] Local OAuth token generated
- [ ] VPS provisioned (2GB+ RAM, Ubuntu)
- [ ] Files uploaded to VPS
- [ ] deploy.sh executed successfully
- [ ] .env and credentials copied
- [ ] Health check passed
- [ ] Test pipeline run successful
- [ ] PM2 daemon started
- [ ] PM2 auto-start configured
- [ ] Logs verified
- [ ] Firewall enabled
- [ ] Backup script configured

---

## Next Steps

1. **Monitor first few runs**: Check logs daily for first week
2. **Verify uploads**: Confirm videos appear on YouTube
3. **Optimize schedule**: Adjust based on audience analytics
4. **Scale if needed**: Upgrade VPS if processing is slow

---

## Support

- View logs: `pm2 logs yt-automation`
- Health status: `cat channel/health_status.json | jq`
- Quota dashboard: Check SQLite database
- Error history: `cat channel/error_history.json`

**System is now production-ready and fully automated! 🚀**
