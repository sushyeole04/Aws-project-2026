#!/bin/bash
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

cd /home/ec2-user/app
# Start the server (assuming server.js is the entry point, update if different)
pm2 start server.js --name "node-app"
pm2 save
pm2 startup | grep "sudo env" | bash || true
