#!/usr/bin/env bash
# System Info — prints OS, CPU, memory, disk, and network info.
# Useful for verifying the execution environment of a USO runner.

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  SYSTEM INFORMATION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo ""
echo "── OS ──────────────────────────────────────────"
uname -a

echo ""
echo "── CPU ─────────────────────────────────────────"
if command -v nproc &>/dev/null; then
  echo "Cores: $(nproc)"
fi
if [ -f /proc/cpuinfo ]; then
  grep "model name" /proc/cpuinfo | head -1
fi

echo ""
echo "── Memory ──────────────────────────────────────"
if command -v free &>/dev/null; then
  free -h
elif command -v vm_stat &>/dev/null; then
  vm_stat | head -10
fi

echo ""
echo "── Disk ────────────────────────────────────────"
df -h .

echo ""
echo "── Environment Variables (non-secret) ──────────"
env | grep -v -iE 'secret|token|password|key|fernet' | sort

echo ""
echo "── Installed Tools ─────────────────────────────"
for cmd in python3 node npm curl wget jq git docker; do
  if command -v "$cmd" &>/dev/null; then
    echo "  ✅ $cmd — $($cmd --version 2>&1 | head -1)"
  else
    echo "  ❌ $cmd — not found"
  fi
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
