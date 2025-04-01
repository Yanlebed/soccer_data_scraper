#!/bin/bash
# Main deployment script for Football Statistics Scraper

set -e  # Exit on error
export AWS_PAGER=""

# Configuration
REGION="eu-west-1"  # Change to your region
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
EMAIL="bookly.beekly@gmail.com"  # Change to your email
STACK_PREFIX="football-scraper"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting deployment of Football Statistics Scraper...${NC}"

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}AWS CLI is not installed. Please install it first.${NC}"
    exit 1
fi

# Check if AWS credentials are configured
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}AWS credentials are not configured. Please run 'aws configure' first.${NC}"
    exit 1
fi

# Create SNS Topic for notifications
echo -e "${YELLOW}Creating SNS topic for notifications...${NC}"
aws cloudformation deploy \
    --template-file ../cloudformation/sns-setup.yaml \
    --stack-name "${STACK_PREFIX}-sns" \
    --parameter-overrides \
        EmailAddress="$EMAIL" \
        TopicName="FootballScraperAlerts" \
    --capabilities CAPABILITY_NAMED_IAM

# Get SNS Topic ARN
SNS_TOPIC_ARN=$(aws cloudformation describe-stacks \
    --stack-name "${STACK_PREFIX}-sns" \
    --query "Stacks[0].Outputs[?OutputKey=='ScraperAlertsTopicArn'].OutputValue" \
    --output text)

echo -e "${GREEN}SNS Topic ARN: $SNS_TOPIC_ARN${NC}"

# Create DynamoDB tables
echo -e "${YELLOW}Creating DynamoDB tables...${NC}"
aws dynamodb create-table \
    --table-name football_matches \
    --attribute-definitions AttributeName=match_id,AttributeType=S \
    --key-schema AttributeName=match_id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region "$REGION" || echo -e "${YELLOW}Table football_matches may already exist${NC}"

aws dynamodb create-table \
    --table-name football_stats \
    --attribute-definitions AttributeName=match_id,AttributeType=S \
    --key-schema AttributeName=match_id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region "$REGION" || echo -e "${YELLOW}Table football_stats may already exist${NC}"

# Store Google credentials in Secrets Manager
echo -e "${YELLOW}Do you want to upload Google credentials to AWS Secrets Manager? (y/n)${NC}"
read -r upload_credentials

if [[ "$upload_credentials" == "y" ]]; then
    echo -e "${YELLOW}Enter path to Google credentials JSON file:${NC}"
    read -r credentials_path

    if [[ -f "$credentials_path" ]]; then
        aws secretsmanager create-secret \
            --name "football-scraper/google-credentials" \
            --description "Google service account credentials for football scraper" \
            --secret-string "file://$credentials_path" \
            --region "$REGION" || aws secretsmanager update-secret \
                --secret-id "football-scraper/google-credentials" \
                --secret-string "file://$credentials_path" \
                --region "$REGION"

        echo -e "${GREEN}Credentials stored in Secrets Manager${NC}"
    else
        echo -e "${RED}Credentials file not found. Skipping.${NC}"
    fi
fi

# Create IAM role for Lambda
echo -e "${YELLOW}Creating IAM role for Lambda functions...${NC}"
aws cloudformation deploy \
    --template-file ../cloudformation/iam.yaml \
    --stack-name "${STACK_PREFIX}-iam" \
    --capabilities CAPABILITY_NAMED_IAM

# Get IAM role ARN
LAMBDA_ROLE_ARN=$(aws cloudformation describe-stacks \
    --stack-name "${STACK_PREFIX}-iam" \
    --query "Stacks[0].Outputs[?OutputKey=='LambdaRoleArn'].OutputValue" \
    --output text)

echo -e "${GREEN}Lambda Role ARN: $LAMBDA_ROLE_ARN${NC}"

# Create Playwright Lambda Layer
echo -e "${YELLOW}Creating Playwright Lambda Layer...${NC}"
./update_layer.sh

# Get Lambda Layer ARN
LAYER_ARN=$(aws lambda list-layer-versions \
    --layer-name playwright \
    --query "LayerVersions[0].LayerVersionArn" \
    --output text)

echo -e "${GREEN}Lambda Layer ARN: $LAYER_ARN${NC}"

# Package and deploy Lambda functions
echo -e "${YELLOW}Packaging Lambda functions...${NC}"
./package_lambda.sh

# Create Lambda functions
echo -e "${YELLOW}Creating Lambda functions...${NC}"
aws cloudformation deploy \
    --template-file ../cloudformation/lambda.yaml \
    --stack-name "${STACK_PREFIX}-lambda" \
    --parameter-overrides \
        LambdaRoleArn="$LAMBDA_ROLE_ARN" \
        PlaywrightLayerArn="$LAYER_ARN" \
        SNSTopicArn="$SNS_TOPIC_ARN" \
        ScheduleUpdaterS3Key="schedule_updater.zip" \
        StatsCollectorS3Key="stats_collector.zip" \
    --capabilities CAPABILITY_NAMED_IAM

# Create CloudWatch Alarms
echo -e "${YELLOW}Creating CloudWatch Alarms...${NC}"
aws cloudformation deploy \
    --template-file ../cloudformation/alarms.yaml \
    --stack-name "${STACK_PREFIX}-alarms" \
    --parameter-overrides \
        SnsTopicArn="$SNS_TOPIC_ARN" \
        ScheduleUpdaterFunctionName="FootballScheduleUpdater" \
        StatsCollectorFunctionName="FootballStatsCollector"

# Create daily EventBridge rule for ScheduleUpdater
echo -e "${YELLOW}Creating daily EventBridge rule...${NC}"
SCHEDULE_UPDATER_ARN=$(aws cloudformation describe-stacks \
    --stack-name "${STACK_PREFIX}-lambda" \
    --query "Stacks[0].Outputs[?OutputKey=='ScheduleUpdaterArn'].OutputValue" \
    --output text)

aws events put-rule \
    --name "DailyFootballScheduleUpdate" \
    --schedule-expression "cron(0 6 * * ? *)" \
    --state ENABLED

aws events put-targets \
    --rule "DailyFootballScheduleUpdate" \
    --targets "Id"="1","Arn"="$SCHEDULE_UPDATER_ARN"

aws lambda add-permission \
    --function-name FootballScheduleUpdater \
    --statement-id "DailyFootballScheduleUpdate-event" \
    --action "lambda:InvokeFunction" \
    --principal "events.amazonaws.com" \
    --source-arn "arn:aws:events:$REGION:$ACCOUNT_ID:rule/DailyFootballScheduleUpdate"

echo -e "${GREEN}Deployment completed successfully!${NC}"
echo -e "${YELLOW}Next steps:${NC}"
echo -e "1. Check your email and confirm the SNS subscription"
echo -e "2. Test the deployment by running a test invocation of the schedule updater"
echo -e "3. Check CloudWatch Logs for any issues"