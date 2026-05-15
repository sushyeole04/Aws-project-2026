#!/bin/bash
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

# Install nvm and node if not present
if ! command -v node &> /dev/null
then
    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
    \. "$NVM_DIR/nvm.sh"
    nvm install 18
fi

# Install pm2 if not present
if ! command -v pm2 &> /dev/null
then
    npm install -g pm2
fi

cd /home/ec2-user/app
npm install --production
