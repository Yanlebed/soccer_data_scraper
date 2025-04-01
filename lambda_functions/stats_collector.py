"""
Lambda function for collecting match statistics using Scrapy.
"""
import json
import logging
import os
from datetime import datetime
from typing import Dict, Any

from scraper.utils import run_spider_for_statistics
from models.match_data import MatchInfo, MatchStatistics
from storage.dynamodb import DynamoDBManager
from storage.google_sheets import GoogleSheetsManager
from utils.error_handler import ErrorHandler
from utils.credentials import get_google_credentials

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize error handler
error_handler = ErrorHandler(
    function_name='FootballStatsCollector',
    sns_topic_arn=os.environ.get('SNS_TOPIC_ARN')
)


def lambda_handler(event, context):
    """
    Collect match statistics for a specific match.

    Args:
        event: Lambda event with match details
        context: Lambda context

    Returns:
        Response dictionary
    """
    try:
        logger.info(f"Starting statistics collection for event: {json.dumps(event)}")

        # Load Google credentials from Secrets Manager
        creds_path = get_google_credentials()
        logger.info(f"Loaded Google credentials to {creds_path}")

        # Extract match info from event
        match_id = event.get('match_id')
        if not match_id:
            raise ValueError("Missing match_id in event")

        team = event.get('team')
        if not team:
            raise ValueError("Missing team in event")

        opponent = event.get('opponent')
        if not opponent:
            raise ValueError("Missing opponent in event")

        is_home = event.get('is_home')
        if is_home is None:  # Could be False
            raise ValueError("Missing is_home in event")

        match_datetime_str = event.get('match_datetime')
        if not match_datetime_str:
            raise ValueError("Missing match_datetime in event")

        stats_url = event.get('stats_url')
        if not stats_url:
            raise ValueError("Missing stats_url in event")

        # Parse match datetime
        try:
            match_datetime = datetime.fromisoformat(match_datetime_str)
        except Exception as e:
            raise ValueError(f"Invalid match_datetime format: {str(e)}")

        logger.info(f"Processing match: {team} vs {opponent} ({match_id})")

        # Initialize components
        db_manager = DynamoDBManager()
        sheets_manager = GoogleSheetsManager(credentials_path=creds_path)

        # Initialize Google Sheets
        logger.info("Initializing Google Sheets")
        sheets_initialized = sheets_manager.initialize()
        if not sheets_initialized:
            logger.warning("Failed to initialize Google Sheets, will continue with database only")

        # Run the Scrapy spider to collect statistics
        logger.info(f"Running spider for match statistics: {stats_url}")
        stats_dict = run_spider_for_statistics(
            match_id=match_id,
            team_name=team,
            is_home=is_home,
            opponent=opponent,
            stats_url=stats_url
        )

        if not stats_dict:
            raise Exception(f"Failed to extract statistics for {team} vs {opponent}")

        # Convert dictionary to MatchStatistics object
        stats = MatchStatistics(
            match_id=stats_dict['match_id'],
            team=stats_dict['team'],
            opponent=stats_dict['opponent'],
            is_home=stats_dict['is_home'],
            match_datetime=stats_dict['match_datetime'],
            collection_datetime=datetime.now(),
            shots=stats_dict['shots'],
            shots_on_target=stats_dict['shots_on_target'],
            goals=stats_dict['goals'],
            source=stats_dict.get('source', 'totalcorner')
        )

        logger.info(
            f"Statistics extracted: shots={stats.shots}, shots_on_target={stats.shots_on_target}, goals={stats.goals}")

        # Save to database
        logger.info("Saving statistics to database")
        db_success = db_manager.save_match_statistics(stats)
        if not db_success:
            logger.warning("Failed to save statistics to database")

        # Update Google Sheets if initialized
        if sheets_initialized:
            try:
                logger.info("Updating Google Sheets")
                all_stats = db_manager.get_all_match_statistics()
                sheets_success = sheets_manager.update_match_statistics(all_stats)
                if not sheets_success:
                    logger.warning("Failed to update Google Sheets")
            except Exception as sheets_error:
                logger.error(f"Error updating Google Sheets: {str(sheets_error)}")

        # Report success
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Statistics collection completed',
                'match_id': match_id,
                'team': team,
                'opponent': opponent,
                'shots': stats.shots,
                'shots_on_target': stats.shots_on_target,
                'goals': stats.goals
            })
        }

    except Exception as e:
        # Handle unexpected errors
        return error_handler.handle_exception(
            e,
            context,
            custom_message=f"Failed to collect statistics for match {event.get('match_id', 'unknown')}"
        )