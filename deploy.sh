#!/usr/bin/env bash
# ============================================================
# deploy.sh — Digital Will Executor Deployment Script
# ============================================================
# Usage:
#   chmod +x deploy.sh
#   ./deploy.sh <your-hf-username> <space-name>
#
# Example:
#   ./deploy.sh john_doe digital-will-executor
# ============================================================

set -e

HF_USERNAME=${1:-"your-hf-username"}
SPACE_NAME=${2:-"digital-will-executor"}
HF_REPO="$HF_USERNAME/$SPACE_NAME"

echo ""
echo "============================================"
echo "  Digital Will Executor — Deployment Script"
echo "============================================"
echo "Repo: $HF_REPO"
echo ""

# ── Step 1: Git init ──────────────────────────────────────────────────────────
echo "[1/5] Initializing git..."
git init
git add .
git commit -m "Initial commit — Digital Will Executor OpenEnv"

# ── Step 2: Create HF Space ───────────────────────────────────────────────────
echo ""
echo "[2/5] Creating Hugging Face Space..."
huggingface-cli repo create "$SPACE_NAME" --type space --space-sdk docker --yes || true

# ── Step 3: Add remote and push ───────────────────────────────────────────────
echo ""
echo "[3/5] Pushing to HF Space..."
git remote remove hf 2>/dev/null || true
git remote add hf "https://huggingface.co/spaces/$HF_REPO"
git push hf main --force

# ── Step 4: Set secrets ───────────────────────────────────────────────────────
echo ""
echo "[4/5] Setting Space secrets..."
echo ""
echo "  Run these manually in your terminal:"
echo ""
echo "  huggingface-cli repo secrets create $HF_REPO HF_TOKEN <your_token>"
echo "  huggingface-cli repo secrets create $HF_REPO MODEL_NAME 'Qwen/Qwen2.5-72B-Instruct'"
echo "  huggingface-cli repo secrets create $HF_REPO API_BASE_URL 'https://router.huggingface.co/v1'"
echo ""

# ── Step 5: Print Space URL ───────────────────────────────────────────────────
echo "[5/5] Done!"
echo ""
echo "  Your Space URL: https://$HF_USERNAME-$SPACE_NAME.hf.space"
echo "  Health check:   https://$HF_USERNAME-$SPACE_NAME.hf.space/health"
echo "  API docs:       https://$HF_USERNAME-$SPACE_NAME.hf.space/docs"
echo ""
echo "  Run validation:"
echo "  ./validate-submission.sh https://$HF_USERNAME-$SPACE_NAME.hf.space"
echo ""
