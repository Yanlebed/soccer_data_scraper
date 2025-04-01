# lambda_functions/schedule_updater.py (updated for Scrapy)
import json
import boto3
import asyncio
import datetime
import logging
from typing import Dict, List
import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from config_totalcorner import TOTALCORNER_TEAMS, COLLECTION_DELAYS
from scraper.totalcorner_spider import TotalCornerSpider
from models.match_data import MatchInfo
from storage.dynamodb import DynamoDBManager
from storage.google_sheets import GoogleSheetsManager
from utils.date_utils import calculate_collection_time
from utils.error_handler import ErrorHandler
from utils.credentials import get_google_credentials

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize error handler
error_handler = ErrorHandler(
    function_name='FootballScheduleUpdater',
    sns_topic_arn=os.environ.get('SNS_TOPIC_ARN')
)

# Initialize AWS clients
events_client = boto3.client('events')
lambda_client = boto3.client('lambda')

def create_stats_collection_rule(match_info):
    """Create an EventBridge rule to trigger statistics collection."""
    try:
        # Calculate when to run the collection
        match_time = match_info.match_datetime
        collection_time = match_info.collection_time

        # Create rule name
        rule_name = f"collect-stats-{match_info.team.replace(' ', '-')}-{match_info.match_id}"
        if len(rule_name) > 64:
            rule_name = rule_name[:60] + hash(rule_name)[-4:]

        # Calculate cron expression (EventBridge uses UTC)
        cron_expression = f"cron({collection_time.minute} {collection_time.hour} {collection_time.day} {collection_time.month} ? {collection_time.year})"

        logger.info(f"Creating rule {rule_name} with schedule {cron_expression}")

        # Create the rule
        events_client.put_rule(
            Name=rule_name,
            ScheduleExpression=cron_expression,
            State='ENABLED',
            Description=f"Collect stats for {match_info.team} vs {match_info.opponent} on {match_time}"
        )

        # Create input for the target Lambda function
        input_json = {
            'match_id': match_info.match_id,
            'team': match_info.team,
            'opponent': match_info.opponent,
            'is_home': match_info.is_home,
            'match_datetime': match_info.match_datetime.isoformat(),
            'stats_url': match_info.stats_url
        }

        # Add the Lambda function as a target
        events_client.put_targets(
            Rule=rule_name,
            Targets=[
                {
                    'Id': '1',
                    'Arn': os.environ.get('STATS_COLLECTOR_ARN'),
                    'Input': json.dumps(input_json)
                }
            ]
        )

        # Add permission for EventBridge to invoke Lambda
        try:
            lambda_client.add_permission(
                FunctionName='FootballStatsCollector',
                StatementId=f'{rule_name}-event',
                Action='lambda:InvokeFunction',
                Principal='events.amazonaws.com',
                SourceArn=f"arn:aws:events:{os.environ.get('AWS_REGION')}:{os.environ.get('AWS_ACCOUNT_ID')}:rule/{rule_name}"
            )
        except lambda_client.exceptions.ResourceConflictException:
            logger.info(f"Permission already exists for rule {rule_name}")

        logger.info(f"Successfully created rule {rule_name}")
        return rule_name

    except Exception as e:
        logger.error(f"Error creating rule for match {match_info.match_id}: {str(e)}")
        return None

def get_upcoming_matches(teams):
    """Get upcoming matches for all teams using Scrapy."""
    all_matches = []
    process = CrawlerProcess(get_project_settings())

    for team in teams:
        spider = TotalCornerSpider(team_id=team['id'], team_name=team['name'])
        process.crawl(spider)
        process.start()  # This will block until the crawl is complete

        for result in spider.results:
            # Convert to MatchInfo objects
            match_info = MatchInfo(
                match_id=result['match_id'],
                team=result['team'],
                opponent=result['opponent'],
                is_home=result['is_home'],
                match_datetime=result['match_datetime'],
                competition_type='default'
            )
            # Add additional field
            match_info.stats_url = result['stats_url']
            # Calculate collection time
            match_info.collection_time = calculate_collection_time(
                match_info.match_datetime,
                match_info.competition_type,
                COLLECTION_DELAYS
            )
            all_matches.append(match_info)

    return all_matches

def lambda_handler(event, context):
    """Lambda handler function."""
    try:
        # Load Google credentials
        creds_path = get_google_credentials()
        logger.info(f"Loaded Google credentials from {creds_path}")

        # Get upcoming matches
        all_matches = []
        processed_match_ids = set()

        # Get matches for all teams
        matches = get_upcoming_matches(TOTALCORNER_TEAMS)

        # Filter out duplicates
        for match in matches:
            if match.match_id not in processed_match_ids:
                all_matches.append(match)
                processed_match_ids.add(match.match_id)
            else:
                logger.info(f"Skipping duplicate match {match.match_id}")

        # Sort matches by date
        all_matches.sort(key=lambda x: x.match_datetime)

        # Save to database
        db_manager = DynamoDBManager()
        db_manager.save_scheduled_matches(all_matches)

        # Create EventBridge rules for each match
        for match in all_matches:
            create_stats_collection_rule(match)

        # Update Google Sheets if needed
        try:
            sheets_manager = GoogleSheetsManager(credentials_path=creds_path)
            sheets_manager.initialize()
            # Optional: Update a sheet with schedule information
        except Exception as sheets_error:
            logger.error(f"Error updating Google Sheets: {str(sheets_error)}")

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Schedule update completed',
                'matches_found': len(all_matches)
            })
        }

    except Exception as e:
        return error_handler.handle_exception(e, context)