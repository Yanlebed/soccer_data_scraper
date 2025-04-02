"""
Utility functions for scraping with Scrapy.
"""
import os
import tempfile
import logging
from typing import Dict, List, Optional, Any
from scrapy.crawler import CrawlerProcess
from scrapy.settings import Settings

from config_totalcorner import SCRAPY_SETTINGS
from scraper.totalcorner_spider import TotalCornerSpider

logger = logging.getLogger(__name__)


def get_scrapy_settings():
    """
    Get settings for Scrapy crawler.

    Returns:
        Scrapy settings object
    """
    settings = Settings()
    for key, value in SCRAPY_SETTINGS.items():
        settings.set(key, value)

    # Disable logging for production
    if os.environ.get('AWS_EXECUTION_ENV'):
        settings.set('LOG_LEVEL', 'ERROR')

    return settings


def run_spider_for_matches(team_id: str, team_name: str) -> List[Dict]:
    """
    Run a spider to get upcoming matches for a team without using CrawlerProcess.

    Args:
        team_id: Team ID on TotalCorner
        team_name: Team name

    Returns:
        List of match dictionaries
    """
    # Create the spider
    spider = TotalCornerSpider(team_id=team_id, team_name=team_name)

    # Manually execute the spider's requests
    results = []

    # Get requests from spider
    for request in spider.start_requests():
        # In a real scenario, we would need to fetch the response
        # but for Lambda, we would need to use requests library directly
        import requests

        # Convert scrapy request to requests
        headers = dict(request.headers)
        url = request.url

        # Make the request
        response = requests.get(url, headers=headers)

        # Parse the HTML using a library like Beautiful Soup
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract data similar to how your spider would
        # This would need to be customized based on your spider's parsing logic
        # For simplicity, this is a placeholder

        # Add results to the list
        results.extend(spider.results)

    return results


def run_spider_for_statistics(match_id: str, team_name: str, is_home: bool,
                              opponent: str, stats_url: str) -> Optional[Dict]:
    """
    Run a spider to collect statistics for a match.

    Args:
        match_id: Match ID
        team_name: Team name
        is_home: Whether the team is playing at home
        opponent: Opponent team name
        stats_url: URL for the statistics page

    Returns:
        Statistics dictionary or None if extraction failed
    """
    try:
        # Configure crawler process
        process = CrawlerProcess(get_scrapy_settings())

        # Create and configure spider
        spider = TotalCornerSpider(
            match_id=match_id,
            team_name=team_name,
            is_home=is_home,
            opponent=opponent,
            stats_url=stats_url
        )

        # Run the spider
        process.crawl(spider)
        process.start()  # This blocks until the crawl is finished

        # Get results
        if spider.results:
            return spider.results[0]  # Return the first result

    except Exception as e:
        logger.error(f"Error collecting statistics for match {match_id}: {e}")

    return None