#!/bin/bash
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

# Stop existing PM2 processes safely
if command -v pm2 &> /dev/null
then
    pm2 stop all || true
    pm2 delete all || true
fi
