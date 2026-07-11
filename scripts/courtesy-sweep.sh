#!/bin/bash
# Courtesy invariant-9 sweep, before firing any deepwiki-open generation against a shared
# (overflow-2/3/4) account. Widened after a real gap (garvis-4p24 adjacent finding, 2026-07-11): the
# original per-fire sweep only grepped for `cope-tools (relabel|optimize|clr)` BY NAME — it missed a
# LIVE `comprehensive-label-review` job (a different cope-tools-py skill/verb spawning bursty,
# short-lived `claude_agent_sdk` subprocess calls) sitting right underneath two consecutive fires.
# Point-in-time `ps` snapshots can miss fast/bursty subprocess activity between bursts even when the
# job is genuinely running; this sweep widens the net to catch the underlying MECHANISM (any
# claude_agent_sdk bundled-CLI subprocess, any cope-tools invocation) rather than a closed list of
# verb names, so a future skill/verb never needs a matching update here.
#
# Usage: ./courtesy-sweep.sh
# Exit 0 = looks clear. Exit 1 = a real signal found — read the printed detail before firing.
# This is advisory evidence for a human/agent decision, never an automated gate (fleet invariant 9
# explicitly bans a load-average auto-governor on this box) — it prints what it finds and exits
# non-zero on a hit; it does not, and must never, block or kill anything itself.

set -u
FOUND=0

echo "=== courtesy sweep: any process bound to a shared account's CLAUDE_CONFIG_DIR ==="
HITS=$(ps aux | grep -v grep | grep -iE "overflow-2|overflow-3|overflow-4" | \
  grep -v "attention-tick-poke\|jacques resume\|jacques new\|shell-snapshots")
if [ -n "$HITS" ]; then
  echo "$HITS"
  FOUND=1
else
  echo "(none — clear)"
fi

echo "=== courtesy sweep: ANY cope-tools invocation (not just relabel/optimize/clr by name) ==="
HITS=$(ps aux | grep -v grep | grep -i "cope-tools ")
if [ -n "$HITS" ]; then
  echo "$HITS"
  FOUND=1
else
  echo "(none — clear)"
fi

echo "=== courtesy sweep: ANY live claude_agent_sdk bundled CLI subprocess (any skill/verb) ==="
HITS=$(ps aux | grep -v grep | grep -i "claude_agent_sdk")
if [ -n "$HITS" ]; then
  echo "$HITS" | cut -c1-200
  FOUND=1
else
  echo "(none — clear; NOTE this class is bursty/short-lived, a clean snapshot here is weaker evidence than the process-name checks above, not a guarantee)"
fi

echo "=== box load ==="
uptime

if [ "$FOUND" -eq 1 ]; then
  echo "=== VERDICT: signal found — review before firing ==="
  exit 1
else
  echo "=== VERDICT: clear ==="
  exit 0
fi
