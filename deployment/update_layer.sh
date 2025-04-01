#!/bin/bash
# Script to create and update the Scrapy Lambda layer with improved error handling

set -e  # Exit on error

# Configuration
REGION="eu-west-1"  # Change to your region
LAYER_NAME="scrapy-layer"
MAX_RETRIES=3

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Creating Scrapy Lambda layer...${NC}"

# Create temporary directory
TEMP_DIR=$(mktemp -d)
cd "$TEMP_DIR"

# Create directory structure
mkdir -p python/lib/python3.12/site-packages

# Install dependencies with increased verbosity
echo -e "${YELLOW}Installing dependencies...${NC}"
pip install -v scrapy==2.11.0 gspread==5.12.0 google-auth==2.23.4 gspread-dataframe==3.3.1 pandas==2.1.1 boto3==1.34.51 -t python/lib/python3.12/site-packages

# Create zip file
echo -e "${YELLOW}Creating zip file...${NC}"
zip -r "$LAYER_NAME.zip" python

# Check file size
SIZE=$(du -h "$LAYER_NAME.zip" | cut -f1)
echo -e "${GREEN}Layer size: $SIZE${NC}"

# Layer size limit is 250MB unzipped
if [ $(unzip -l "$LAYER_NAME.zip" | tail -1 | awk '{print $1}') -gt 262144000 ]; then
    echo -e "${RED}Warning: Layer exceeds size limit (250MB unzipped)${NC}"
    echo -e "${YELLOW}Consider removing unused dependencies or creating multiple layers${NC}"
fi

# Split the zip file into smaller chunks to improve upload reliability
echo -e "${YELLOW}Checking if layer needs to be split...${NC}"
ZIP_SIZE_BYTES=$(stat -c%s "$LAYER_NAME.zip")
# 50MB in bytes
CHUNK_SIZE=52428800

if [ $ZIP_SIZE_BYTES -gt $CHUNK_SIZE ]; then
    echo -e "${YELLOW}Layer file is large ($SIZE). Trying direct upload first...${NC}"

    # Retry mechanism for uploading layer
    for ((i=1; i<=$MAX_RETRIES; i++)); do
        echo -e "${YELLOW}Upload attempt $i of $MAX_RETRIES...${NC}"
        if aws lambda publish-layer-version \
            --layer-name "$LAYER_NAME" \
            --description "Scrapy and dependencies for web scraping" \
            --zip-file "fileb://$LAYER_NAME.zip" \
            --compatible-runtimes python3.12 \
            --region "$REGION" \
            --cli-connect-timeout 300 \
            --cli-read-timeout 300; then

            echo -e "${GREEN}Layer uploaded successfully!${NC}"
            UPLOAD_SUCCESS=true
            break
        else
            echo -e "${RED}Upload attempt $i failed${NC}"

            if [ $i -eq $MAX_RETRIES ]; then
                echo -e "${YELLOW}Direct upload failed. Trying S3 upload method...${NC}"

                # Create a unique bucket name or use an existing one
                ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
                S3_BUCKET="lambda-layer-upload-$ACCOUNT_ID"

                # Check if bucket exists, create if it doesn't
                if ! aws s3api head-bucket --bucket "$S3_BUCKET" 2>/dev/null; then
                    echo -e "${YELLOW}Creating S3 bucket for layer upload...${NC}"
                    aws s3 mb "s3://$S3_BUCKET" --region "$REGION"
                fi

                # Upload to S3
                echo -e "${YELLOW}Uploading layer to S3...${NC}"
                aws s3 cp "$LAYER_NAME.zip" "s3://$S3_BUCKET/$LAYER_NAME.zip" --cli-connect-timeout 300

                # Create layer from S3
                echo -e "${YELLOW}Creating layer from S3...${NC}"
                aws lambda publish-layer-version \
                    --layer-name "$LAYER_NAME" \
                    --description "Scrapy and dependencies for web scraping" \
                    --content "S3Bucket=$S3_BUCKET,S3Key=$LAYER_NAME.zip" \
                    --compatible-runtimes python3.12 \
                    --region "$REGION"

                UPLOAD_SUCCESS=true
                break
            fi

            # Wait before retrying
            sleep 5
        fi
    done
else
    # File is small enough for direct upload
    echo -e "${YELLOW}Uploading layer to AWS...${NC}"
    aws lambda publish-layer-version \
        --layer-name "$LAYER_NAME" \
        --description "Scrapy and dependencies for web scraping" \
        --zip-file "fileb://$LAYER_NAME.zip" \
        --compatible-runtimes python3.12 \
        --region "$REGION" \
        --cli-connect-timeout 300 \
        --cli-read-timeout 300

    UPLOAD_SUCCESS=true
fi

# Clean up
cd - > /dev/null
rm -rf "$TEMP_DIR"

if [ "$UPLOAD_SUCCESS" = true ]; then
    echo -e "${GREEN}Scrapy Lambda layer created and uploaded successfully!${NC}"
else
    echo -e "${RED}Failed to upload Lambda layer after multiple attempts.${NC}"
    echo -e "${YELLOW}Please check your AWS credentials and network connection.${NC}"
    exit 1
fi