#!/bin/bash
# Script to create a Scrapy Lambda layer using S3 for reliable uploads

set -e  # Exit on error

# Configuration
REGION="eu-west-1"  # Change to your region
LAYER_NAME="scrapy-layer"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
S3_BUCKET="football-scraper-deployment-$ACCOUNT_ID"  # Reuse the same bucket from deploy.sh

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Creating Scrapy Lambda layer...${NC}"

# Check if S3 bucket exists, create if it doesn't
if ! aws s3api head-bucket --bucket "$S3_BUCKET" 2>/dev/null; then
    echo -e "${YELLOW}Creating S3 bucket $S3_BUCKET...${NC}"
    aws s3 mb "s3://$S3_BUCKET" --region "$REGION"
fi

# Create temporary directory
TEMP_DIR=$(mktemp -d)
cd "$TEMP_DIR"

# Create directory structure
mkdir -p python/lib/python3.12/site-packages

# Install dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
pip install scrapy==2.11.0 gspread==5.12.0 google-auth==2.23.4 gspread-dataframe==3.3.1 pandas==2.1.1 boto3==1.34.51 -t python/lib/python3.12/site-packages

# Create zip file
echo -e "${YELLOW}Creating zip file...${NC}"
zip -r "$LAYER_NAME.zip" python

# Check file size
SIZE=$(du -h "$LAYER_NAME.zip" | cut -f1)
echo -e "${GREEN}Layer size: $SIZE${NC}"

# Upload the zip file to S3
echo -e "${YELLOW}Uploading layer zip to S3 bucket...${NC}"
aws s3 cp "$LAYER_NAME.zip" "s3://$S3_BUCKET/$LAYER_NAME.zip"

# Create the Lambda layer from the S3 file
echo -e "${YELLOW}Creating Lambda layer from S3...${NC}"
aws lambda publish-layer-version \
    --layer-name "$LAYER_NAME" \
    --description "Scrapy and dependencies for web scraping" \
    --content "S3Bucket=$S3_BUCKET,S3Key=$LAYER_NAME.zip" \
    --compatible-runtimes python3.12 \
    --region "$REGION"

# Clean up
cd - > /dev/null
rm -rf "$TEMP_DIR"

echo -e "${GREEN}Scrapy Lambda layer created and uploaded successfully!${NC}"