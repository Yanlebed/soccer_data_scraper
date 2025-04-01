#!/bin/bash
# Script to update the Lambda functions

set -e  # Exit on error

# Configuration
REGION="eu-west-1"  # Change to your region
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
S3_BUCKET="football-scraper-deployment-${ACCOUNT_ID}"  # S3 bucket for deployment artifacts

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Packaging and updating Lambda functions...${NC}"

# Create directories for Lambda packages
echo -e "${YELLOW}Packaging Lambda functions...${NC}"
mkdir -p build/schedule_updater
mkdir -p build/stats_collector

# Package ScheduleUpdater
echo -e "${YELLOW}Packaging ScheduleUpdater...${NC}"
cp -r ../models ../scraper ../storage ../utils ../config_totalcorner.py ../lambda_functions/schedule_updater.py build/schedule_updater/
mv build/schedule_updater/schedule_updater.py build/schedule_updater/lambda_function.py

# Create zip package
cd build/schedule_updater
zip -r ../../schedule_updater.zip .
cd ../..

# Upload to S3
echo -e "${YELLOW}Uploading ScheduleUpdater to S3...${NC}"
aws s3 cp schedule_updater.zip "s3://$S3_BUCKET/schedule_updater.zip"

# Update the Lambda function
echo -e "${YELLOW}Updating ScheduleUpdater Lambda function...${NC}"
aws lambda update-function-code \
    --function-name FootballScheduleUpdater \
    --s3-bucket "$S3_BUCKET" \
    --s3-key schedule_updater.zip \
    --region "$REGION"

# Package StatsCollector
echo -e "${YELLOW}Packaging StatsCollector...${NC}"
cp -r ../models ../scraper ../storage ../utils ../config_totalcorner.py ../lambda_functions/stats_collector.py build/stats_collector/
mv build/stats_collector/stats_collector.py build/stats_collector/lambda_function.py

# Create zip package
cd build/stats_collector
zip -r ../../stats_collector.zip .
cd ../..

# Upload to S3
echo -e "${YELLOW}Uploading StatsCollector to S3...${NC}"
aws s3 cp stats_collector.zip "s3://$S3_BUCKET/stats_collector.zip"

# Update the Lambda function
echo -e "${YELLOW}Updating StatsCollector Lambda function...${NC}"
aws lambda update-function-code \
    --function-name FootballStatsCollector \
    --s3-bucket "$S3_BUCKET" \
    --s3-key stats_collector.zip \
    --region "$REGION"

# Clean up
rm -rf build

echo -e "${GREEN}Lambda functions updated successfully!${NC}"