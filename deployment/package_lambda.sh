#!/bin/bash
# Script to package Lambda functions

set -e  # Exit on error

# Configuration
REGION="eu-west-1"  # Change to your region
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
S3_BUCKET="football-scraper-deployment-$ACCOUNT_ID"  # S3 bucket for deployment artifacts

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Packaging Lambda functions...${NC}"

# Create S3 bucket if it doesn't exist
if ! aws s3api head-bucket --bucket "$S3_BUCKET" 2>/dev/null; then
    echo -e "${YELLOW}Creating S3 bucket $S3_BUCKET...${NC}"
    aws s3 mb "s3://$S3_BUCKET" --region "$REGION"
fi

# Create directories
mkdir -p build/schedule_updater
mkdir -p build/stats_collector

# Package ScheduleUpdater
echo -e "${YELLOW}Packaging ScheduleUpdater...${NC}"
cp -r ../models ../scraper ../storage ../utils ../config_totalcorner.py ../lambda_functions/schedule_updater.py build/schedule_updater/
mv build/schedule_updater/schedule_updater.py build/schedule_updater/lambda_function.py

# Modify source imports for Lambda compatibility
cd build/schedule_updater
find . -type f -name "*.py" -exec sed -i 's/from scraper/from scraper/g' {} \;
find . -type f -name "*.py" -exec sed -i 's/from models/from models/g' {} \;
find . -type f -name "*.py" -exec sed -i 's/from storage/from storage/g' {} \;
find . -type f -name "*.py" -exec sed -i 's/from utils/from utils/g' {} \;
cd ../..

# Create zip package
cd build/schedule_updater
zip -r ../../schedule_updater.zip .
cd ../..

# Upload to S3
aws s3 cp schedule_updater.zip "s3://$S3_BUCKET/schedule_updater.zip"

# Package StatsCollector
echo -e "${YELLOW}Packaging StatsCollector...${NC}"
cp -r ../models ../scraper ../storage ../utils ../config_totalcorner.py ../lambda_functions/stats_collector.py build/stats_collector/
mv build/stats_collector/stats_collector.py build/stats_collector/lambda_function.py

# Modify source imports for Lambda compatibility
cd build/stats_collector
find . -type f -name "*.py" -exec sed -i 's/from scraper/from scraper/g' {} \;
find . -type f -name "*.py" -exec sed -i 's/from models/from models/g' {} \;
find . -type f -name "*.py" -exec sed -i 's/from storage/from storage/g' {} \;
find . -type f -name "*.py" -exec sed -i 's/from utils/from utils/g' {} \;
cd ../..

# Create zip package
cd build/stats_collector
zip -r ../../stats_collector.zip .
cd ../..

# Upload to S3
aws s3 cp stats_collector.zip "s3://$S3_BUCKET/stats_collector.zip"

echo -e "${GREEN}Lambda functions packaged and uploaded to S3 successfully!${NC}"

# Clean up
rm -rf build