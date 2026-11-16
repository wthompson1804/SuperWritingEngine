#!/bin/sh
# run the walkthrough at W (default 390) and print the tail
cd /home/user/SuperWritingEngine/house-hunt && BASE=http://localhost:8765 OUT=${OUT:-/tmp/claude-0/-home-user-SuperWritingEngine/8b31bcc0-2748-5d89-ba10-9e09ecbeef66/scratchpad/shots} W=${W:-390} node scripts/site_walkthrough_test.js 2>&1 | tail -${N:-9} | cut -c1-1200
