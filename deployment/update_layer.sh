#!/bin/bash
# Script to create and update the Playwright Lambda layer

set -e  # Exit on error

# Configuration
REGION="eu-west-1"  # Change to your region
LAYER_NAME="playwright"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Creating Playwright Lambda layer...${NC}"

# Create temporary directory
TEMP_DIR=$(mktemp -d)
cd "$TEMP_DIR"

# Create directory structure
mkdir -p python/lib/python3.12/site-packages

# Install dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
pip install playwright==1.40.0 gspread==5.12.0 google-auth==2.23.4 gspread-dataframe==3.3.1 -t python/lib/python3.12/site-packages

# Install Playwright browsers
echo -e "${YELLOW}Installing Playwright browsers...${NC}"

# Navigate to the temp directory
cd "$TEMP_DIR"

# Install Playwright in the Lambda layer directory
pip install -t python/lib/python3.12/site-packages playwright

# Create a script to install browsers
cat > install_browsers.py << 'EOF'
import os
import subprocess
import sys

# Set the browser path to be within our layer
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "./python/lib/python3.12/site-packages/playwright/.local-browsers"

# Run the explicit playwright install command
subprocess.run([
    "python",
    "-m",
    "playwright",
    "install",
    "chromium",
    "--with-deps"
], check=True)
EOF

# Run the installation script
python install_browsers.py

# Create zip file
echo -e "${YELLOW}Creating zip file...${NC}"
zip -r "$LAYER_NAME.zip" python

# Check file size
SIZE=$(du -h "$LAYER_NAME.zip" | cut -f1)
echo -e "${GREEN}Layer size: $SIZE${NC}"

# Layer size limit is 250MB unzipped
if [ $(unzip -l "$LAYER_NAME.zip" | tail -1 | awk '{print $1}') -gt 262144000 ]; then
    echo -e "${RED}Warning: Layer exceeds size limit (250MB unzipped)${NC}"
    echo -e "${YELLOW}Consider removing unused browsers or creating multiple layers${NC}"
fi

# Upload layer to AWS
echo -e "${YELLOW}Uploading layer to AWS...${NC}"
aws lambda publish-layer-version \
    --layer-name "$LAYER_NAME" \
    --description "Playwright and dependencies for web scraping" \
    --zip-file "fileb://$LAYER_NAME.zip" \
    --compatible-runtimes python3.12 \
    --region "$REGION"

# Clean up
cd - > /dev/null
rm -rf "$TEMP_DIR"

echo -e "${GREEN}Playwright Lambda layer created and uploaded successfully!${NC}"