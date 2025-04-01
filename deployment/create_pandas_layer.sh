#!/bin/bash
# Script to create a compatible pandas/numpy layer

set -e  # Exit on error

# Configuration
REGION="eu-west-1"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
S3_BUCKET="football-scraper-deployment-${ACCOUNT_ID}"
LAYER_NAME="pandas-numpy-layer"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Creating compatible pandas/numpy layer...${NC}"

# Create temporary directory
TEMP_DIR=$(mktemp -d)
cd "$TEMP_DIR"

# Create directory structure
mkdir -p python/lib/python3.12/site-packages

# Create virtual environment with compatible versions
echo -e "${YELLOW}Installing compatible pandas and numpy...${NC}"
python -m venv venv
source venv/bin/activate

# Install compatible versions
pip install --no-cache-dir pandas==2.0.3 numpy==1.24.3

# Copy the packages to the layer directory
cp -r venv/lib/python3.12/site-packages/pandas python/lib/python3.12/site-packages/
cp -r venv/lib/python3.12/site-packages/numpy python/lib/python3.12/site-packages/
cp -r venv/lib/python3.12/site-packages/*.dist-info python/lib/python3.12/site-packages/

# Zip the layer
echo -e "${YELLOW}Creating zip file...${NC}"
zip -r "$LAYER_NAME.zip" python

# Upload to S3
echo -e "${YELLOW}Uploading layer to S3...${NC}"
aws s3 cp "$LAYER_NAME.zip" "s3://$S3_BUCKET/$LAYER_NAME.zip"

# Create layer
echo -e "${YELLOW}Creating Lambda layer...${NC}"
LAYER_VERSION=$(aws lambda publish-layer-version \
    --layer-name "$LAYER_NAME" \
    --description "Compatible pandas and numpy libraries" \
    --content "S3Bucket=$S3_BUCKET,S3Key=$LAYER_NAME.zip" \
    --compatible-runtimes python3.12 \
    --region "$REGION" \
    --query 'Version' \
    --output text)

# Clean up
deactivate
cd - > /dev/null
rm -rf "$TEMP_DIR"

echo -e "${GREEN}Created pandas-numpy layer (Version $LAYER_VERSION)${NC}"
echo -e "${GREEN}Layer ARN: arn:aws:lambda:$REGION:$ACCOUNT_ID:layer:$LAYER_NAME:$LAYER_VERSION${NC}"

# Save layer ARN for future use
echo "PANDAS_LAYER_ARN=arn:aws:lambda:$REGION:$ACCOUNT_ID:layer:$LAYER_NAME:$LAYER_VERSION" > pandas_layer_info.txt