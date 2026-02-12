#!/bin/bash

# CloudNest Quick Start Script
# This script helps you set up CloudNest quickly

echo "========================================="
echo "   CloudNest Setup Script 🚀"
echo "   Deploy Anything. Instantly."
echo "========================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python 3 is not installed. Please install Python 3.9 or higher.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Python 3 found${NC}"

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo -e "${RED}pip3 is not installed. Please install pip3.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ pip3 found${NC}"

# Check if MongoDB is running
if ! command -v mongosh &> /dev/null && ! command -v mongo &> /dev/null; then
    echo -e "${YELLOW}⚠ MongoDB client not found. Make sure MongoDB is installed and running.${NC}"
else
    echo -e "${GREEN}✓ MongoDB client found${NC}"
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}⚠ Docker is not installed. Docker is optional but recommended for app deployments.${NC}"
else
    echo -e "${GREEN}✓ Docker found${NC}"
fi

echo ""
echo "Installing Python dependencies..."
pip3 install -r requirements.txt

if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to install dependencies.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Dependencies installed${NC}"

# Create .env if it doesn't exist
if [ ! -f .env ]; then
    echo ""
    echo "Creating .env file from template..."
    cp .env.example .env
    echo -e "${GREEN}✓ .env file created${NC}"
    echo -e "${YELLOW}⚠ Please edit .env file with your configuration (especially SMTP settings)${NC}"
else
    echo -e "${GREEN}✓ .env file already exists${NC}"
fi

# Create apps directory
mkdir -p /var/cloudnest/apps 2>/dev/null || mkdir -p ./apps

echo ""
echo "========================================="
echo -e "${GREEN}✓ Setup Complete!${NC}"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Edit .env file with your configuration:"
echo "   - Set SECRET_KEY to a random string"
echo "   - Configure SMTP settings for emails"
echo "   - Set your DOMAIN and FRONTEND_URL"
echo ""
echo "2. Make sure MongoDB is running:"
echo "   docker run -d -p 27017:27017 mongo:latest"
echo "   OR"
echo "   sudo systemctl start mongodb"
echo ""
echo "3. Start CloudNest:"
echo "   python3 app.py"
echo ""
echo "4. Access the API:"
echo "   http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo ""
echo "========================================="
