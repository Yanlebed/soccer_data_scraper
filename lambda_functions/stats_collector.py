"""
Lambda function for collecting match statistics.
"""
import json
import asyncio
import logging
from dateutil.parser import parse

# Import your existing TotalCorner code
from scraper.browser import BrowserManager
from scraper.totalcorner_parser import extract_match_statistics
from models.match_data import MatchInfo
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
    sns_topic_arn='arn:aws:sns:YOUR_REGION:YOUR_ACCOUNT_ID:FootballScraperAlerts'  # Update this
)


async def collect_stats(event, context):
    """
    Collect match statistics for a specific match.

    Args:
        event: Lambda event with match details
        context: Lambda context

    Returns:
        Response dictionary
    """
    browser_manager = None

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
            match_datetime = parse(match_datetime_str)
        except Exception as e:
            raise ValueError(f"Invalid match_datetime format: {str(e)}")

        # Create MatchInfo object
        match_info = MatchInfo(
            match_id=match_id,
            team=team,
            opponent=opponent,
            is_home=is_home,
            match_datetime=match_datetime,
            stats_url=stats_url
        )

        logger.info(f"Processing match: {team} vs {opponent} ({match_id})")

        # Initialize components
        browser_manager = BrowserManager()
        db_manager = DynamoDBManager()
        sheets_manager = GoogleSheetsManager()

        # Start browser with error handling
        logger.info("Starting browser")
        await browser_manager.start()

        # Initialize Google Sheets
        logger.info("Initializing Google Sheets")
        sheets_initialized = sheets_manager.initialize()
        if not sheets_initialized:
            logger.warning("Failed to initialize Google Sheets, will continue with database only")

        # Navigate to stats page
        logger.info(f"Navigating to {stats_url}")
        page = await browser_manager.new_page()
        success = await browser_manager.navigate(page, stats_url)

        if not success:
            raise Exception(f"Failed to navigate to {stats_url}")

        # Extract statistics
        logger.info("Extracting statistics")
        stats = await extract_match_statistics(page, match_info)

        # Close page
        await page.close()

        if not stats:
            raise Exception(f"Failed to extract statistics for {team} vs {opponent}")

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

    finally:
        # Ensure browser is closed even if an error occurs
        if browser_manager:
            logger.info("Closing browser")
            await browser_manager.stop()


def lambda_handler(event, context):
    """Lambda handler function."""
    try:
        return asyncio.run(collect_stats(event, context))
    except Exception as e:
        return error_handler.handle_exception(e, context)