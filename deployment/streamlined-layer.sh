#!/bin/bash
# Script to create a streamlined Scrapy Lambda layer using S3

set -e  # Exit on error

# Save current directory
ORIGINAL_DIR=$(pwd)

# Configuration
REGION="eu-west-1"  # Change to your region
LAYER_NAME="scrapy-layer"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
S3_BUCKET="football-scraper-deployment-$ACCOUNT_ID"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Creating streamlined Scrapy Lambda layer...${NC}"

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

# Create requirements file with minimal dependencies
cat > requirements.txt << EOF
# Core scraping functionality
scrapy==2.11.0

# Google Sheets integration
gspread==5.12.0
google-auth==2.23.4
gspread-dataframe==3.3.1

# AWS SDK
boto3==1.34.51

# Data processing
pandas==2.1.1
EOF

echo -e "${YELLOW}Installing only critical dependencies...${NC}"
pip install --no-cache-dir -r requirements.txt -t python/lib/python3.12/site-packages

# Remove unnecessary files to reduce size
echo -e "${YELLOW}Cleaning up unnecessary files to reduce layer size...${NC}"
find python -type d -name "__pycache__" -exec rm -rf {} +
find python -type d -name "tests" -exec rm -rf {} +
find python -type d -name "test" -exec rm -rf {} +
find python -type f -name "*.pyc" -delete
find python -type f -name "*.pyo" -delete
find python -type f -name "*.md" -delete
find python -type f -name "*.txt" ! -name "requirements.txt" -delete
find python -type f -name "*.dist-info/RECORD" -delete
find python -type f -name "*.dist-info/WHEEL" -delete
find python -type f -name "*.dist-info/METADATA" -delete

# Create zip file
echo -e "${YELLOW}Creating zip file...${NC}"
zip -r "$LAYER_NAME.zip" python

# Check file size before and after compression
UNZIPPED_SIZE=$(du -b -s python | cut -f1)
UNZIPPED_SIZE_MB=$(echo "scale=2; $UNZIPPED_SIZE / 1048576" | bc)
ZIPPED_SIZE=$(du -b "$LAYER_NAME.zip" | cut -f1)
ZIPPED_SIZE_MB=$(echo "scale=2; $ZIPPED_SIZE / 1048576" | bc)

echo -e "${GREEN}Layer sizes:"
echo -e "Unzipped: $UNZIPPED_SIZE_MB MB ($UNZIPPED_SIZE bytes)"
echo -e "Zipped: $ZIPPED_SIZE_MB MB ($ZIPPED_SIZE bytes)${NC}"

# Check if unzipped size exceeds Lambda's limit
if [ $UNZIPPED_SIZE -gt 262144000 ]; then
    echo -e "${RED}Warning: Unzipped size ($UNZIPPED_SIZE_MB MB) exceeds Lambda's 250MB limit.${NC}"
    echo -e "${YELLOW}Let's create separate layers for core dependencies.${NC}"

    # Clean up and start over with multiple layers
    rm -rf python "$LAYER_NAME.zip"
    mkdir -p core-layer/python/lib/python3.12/site-packages
    mkdir -p utils-layer/python/lib/python3.12/site-packages

    # Install core scrapy only in first layer
    echo -e "${YELLOW}Creating core Scrapy layer...${NC}"
    pip install --no-cache-dir scrapy==2.11.0 -t core-layer/python/lib/python3.12/site-packages

    # Find and remove unnecessary files
    find core-layer -type d -name "__pycache__" -exec rm -rf {} +
    find core-layer -type d -name "tests" -exec rm -rf {} +
    find core-layer -type f -name "*.pyc" -delete

    # Create core layer zip
    cd core-layer
    zip -r "../scrapy-core-layer.zip" python
    cd ..

    # Install utility dependencies in second layer
    echo -e "${YELLOW}Creating utilities layer...${NC}"
    pip install --no-cache-dir gspread==5.12.0 google-auth==2.23.4 gspread-dataframe==3.3.1 boto3==1.34.51 pandas==2.1.1 -t utils-layer/python/lib/python3.12/site-packages

    # Find and remove unnecessary files
    find utils-layer -type d -name "__pycache__" -exec rm -rf {} +
    find utils-layer -type d -name "tests" -exec rm -rf {} +
    find utils-layer -type f -name "*.pyc" -delete

    # Create utils layer zip
    cd utils-layer
    zip -r "../scrapy-utils-layer.zip" python
    cd ..

    # Upload both layers to S3
    echo -e "${YELLOW}Uploading core layer to S3...${NC}"
    aws s3 cp "scrapy-core-layer.zip" "s3://$S3_BUCKET/scrapy-core-layer.zip"

    echo -e "${YELLOW}Uploading utils layer to S3...${NC}"
    aws s3 cp "scrapy-utils-layer.zip" "s3://$S3_BUCKET/scrapy-utils-layer.zip"

    # Create Lambda layers from S3
    echo -e "${YELLOW}Creating core Lambda layer from S3...${NC}"
    CORE_LAYER_VERSION=$(aws lambda publish-layer-version \
        --layer-name "scrapy-core-layer" \
        --description "Scrapy core for web scraping" \
        --content "S3Bucket=$S3_BUCKET,S3Key=scrapy-core-layer.zip" \
        --compatible-runtimes python3.12 \
        --region "$REGION" \
        --query 'Version' \
        --output text)

    echo -e "${YELLOW}Creating utils Lambda layer from S3...${NC}"
    UTILS_LAYER_VERSION=$(aws lambda publish-layer-version \
        --layer-name "scrapy-utils-layer" \
        --description "Utilities for data processing and storage" \
        --content "S3Bucket=$S3_BUCKET,S3Key=scrapy-utils-layer.zip" \
        --compatible-runtimes python3.12 \
        --region "$REGION" \
        --query 'Version' \
        --output text)

    echo -e "${GREEN}Created two separate layers successfully:${NC}"
    echo -e "${GREEN}Scrapy Core Layer (Version $CORE_LAYER_VERSION)${NC}"
    echo -e "${GREEN}Utilities Layer (Version $UTILS_LAYER_VERSION)${NC}"

    # Create a file with layer ARNs for deploy.sh to use
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    CORE_LAYER_ARN="arn:aws:lambda:$REGION:$ACCOUNT_ID:layer:scrapy-core-layer:$CORE_LAYER_VERSION"
    UTILS_LAYER_ARN="arn:aws:lambda:$REGION:$ACCOUNT_ID:layer:scrapy-utils-layer:$UTILS_LAYER_VERSION"

    # Save to the original directory
    echo "CORE_LAYER_ARN=$CORE_LAYER_ARN" > "$ORIGINAL_DIR/layer_info.txt"
    echo "UTILS_LAYER_ARN=$UTILS_LAYER_ARN" >> "$ORIGINAL_DIR/layer_info.txt"
    echo -e "${YELLOW}Layer ARNs saved to layer_info.txt${NC}"

    echo -e "${YELLOW}Note: You'll need to update your CloudFormation template to use both layers.${NC}"
else
    # Upload the zip file to S3
    echo -e "${YELLOW}Uploading layer zip to S3 bucket...${NC}"
    aws s3 cp "$LAYER_NAME.zip" "s3://$S3_BUCKET/$LAYER_NAME.zip"

    # Create the Lambda layer from the S3 file
    echo -e "${YELLOW}Creating Lambda layer from S3...${NC}"
    LAYER_VERSION=$(aws lambda publish-layer-version \
        --layer-name "$LAYER_NAME" \
        --description "Scrapy and dependencies for web scraping" \
        --content "S3Bucket=$S3_BUCKET,S3Key=$LAYER_NAME.zip" \
        --compatible-runtimes python3.12 \
        --region "$REGION" \
        --query 'Version' \
        --output text)

    echo -e "${GREEN}Scrapy Lambda layer (Version $LAYER_VERSION) created and uploaded successfully!${NC}"

    # Create a file with layer ARN for deploy.sh to use
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    LAYER_ARN="arn:aws:lambda:$REGION:$ACCOUNT_ID:layer:$LAYER_NAME:$LAYER_VERSION"

    # Save to the original directory
    echo "LAYER_ARN=$LAYER_ARN" > "$ORIGINAL_DIR/layer_info.txt"
    echo -e "${YELLOW}Layer ARN saved to layer_info.txt${NC}"
fi

# Clean up and return to original directory
cd "$ORIGINAL_DIR"
rm -rf "$TEMP_DIR"