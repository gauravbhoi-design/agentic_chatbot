#!/usr/bin/env bash
set -o errexit

# Install Python dependencies
cd backend
pip install -r requirements.txt

# Build Vue frontend
cd ../frontend
npm install
npm run build
