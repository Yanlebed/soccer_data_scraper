"""
Scrapy spider for TotalCorner website.
"""
import scrapy
import re
import datetime
import logging
from scrapy import signals
from typing import Dict, List, Optional

from config_totalcorner import TOTALCORNER_BASE_URL, TOTALCORNER_SELECTORS

logger = logging.getLogger(__name__)


class TotalCornerSpider(scrapy.Spider):
    name = "totalcorner"

    def __init__(self, team_id=None, team_name=None, match_id=None, stats_url=None,
                 is_home=None, opponent=None, *args, **kwargs):
        """
        Initialize the TotalCorner spider.

        Args:
            team_id: ID of the team for fetching upcoming matches
            team_name: Name of the team
            match_id: ID of the match for fetching statistics
            stats_url: URL of the match statistics page
            is_home: Whether the team is playing at home (for stats collection)
            opponent: Name of the opponent team (for stats collection)
        """
        super(TotalCornerSpider, self).__init__(*args, **kwargs)
        self.team_id = team_id
        self.team_name = team_name
        self.match_id = match_id
        self.stats_url = stats_url
        self.is_home = is_home
        self.opponent = opponent
        self.results = []

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        """Connect signals when spider is created."""
        spider = super(TotalCornerSpider, cls).from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)
        return spider

    def spider_closed(self, spider):
        """Handle spider closed signal."""
        spider.logger.info('Spider closed: %s', spider.name)

    def start_requests(self):
        """
        Start requests based on spider purpose.
        """
        if self.stats_url:
            # Collecting statistics for a specific match
            yield scrapy.Request(url=self.stats_url, callback=self.parse_match_statistics)
        elif self.match_id:
            # Collecting statistics for a specific match by ID
            url = f"{TOTALCORNER_BASE_URL}/stats/{self.match_id}"
            yield scrapy.Request(url=url, callback=self.parse_match_statistics)
        elif self.team_id and self.team_name:
            # Collecting upcoming matches for a team
            url = f"{TOTALCORNER_BASE_URL}/team/view/{self.team_id}"
            yield scrapy.Request(url=url, callback=self.parse_upcoming_matches)

    def parse_upcoming_matches(self, response):
        """
        Parse upcoming matches from team page.
        """
        # Process match rows
        match_rows = response.xpath(TOTALCORNER_SELECTORS["match_rows"])

        for row in match_rows:
            # Extract match details
            date_str = row.xpath(TOTALCORNER_SELECTORS["match_datetime"]).get()
            if not date_str:
                continue

            # Parse date and time
            match_datetime = self.parse_match_datetime(date_str)
            if not match_datetime or match_datetime < datetime.datetime.now():
                continue  # Skip past matches

            # Get team names
            home_team = row.xpath(TOTALCORNER_SELECTORS["home_team"]).get()
            away_team = row.xpath(TOTALCORNER_SELECTORS["away_team"]).get()

            if not home_team or not away_team:
                continue

            # Check if our team is playing
            is_home = self.team_name.lower() in home_team.lower()
            is_away = self.team_name.lower() in away_team.lower()

            if not (is_home or is_away):
                continue

            # Get match details link
            details_link = row.xpath(TOTALCORNER_SELECTORS["match_details_link"]).get()
            if not details_link:
                continue

            # Extract match ID
            match_id = details_link.split("/")[-1]

            # Create match info dictionary
            match_info = {
                'match_id': match_id,
                'team': self.team_name,
                'opponent': away_team if is_home else home_team,
                'is_home': is_home,
                'match_datetime': match_datetime,
                'stats_url': f"{TOTALCORNER_BASE_URL}{details_link}"
            }

            self.results.append(match_info)

    def parse_match_statistics(self, response):
        """
        Parse match statistics from match details page.
        """
        is_home = self.is_home

        # Extract score
        score_text = None
        for text in response.xpath(TOTALCORNER_SELECTORS["match_score"]).getall():
            if "Score:" in text:
                score_text = text
                break

        if not score_text:
            self.logger.error(f"No score found for match {self.match_id}")
            return

        # Parse score
        score_match = re.search(r"Score:\s*(\d+)\s*-\s*(\d+)", score_text)
        if not score_match:
            self.logger.error(f"Invalid score format: {score_text}")
            return

        home_score, away_score = map(int, score_match.groups())
        goals = home_score if is_home else away_score

        # Get shots on target
        shots_on_target_selector = TOTALCORNER_SELECTORS["home_shots_on_target"] if is_home else TOTALCORNER_SELECTORS[
            "away_shots_on_target"]
        shots_on_target_text = response.xpath(shots_on_target_selector).get()
        shots_on_target = int(shots_on_target_text.strip()) if shots_on_target_text else None

        # Get shots off target
        shots_off_target_selector = TOTALCORNER_SELECTORS["home_shots_off_target"] if is_home else \
        TOTALCORNER_SELECTORS["away_shots_off_target"]
        shots_off_target_text = response.xpath(shots_off_target_selector).get()
        shots_off_target = int(shots_off_target_text.strip()) if shots_off_target_text else None

        # Calculate total shots
        shots = None
        if shots_on_target is not None and shots_off_target is not None:
            shots = shots_on_target + shots_off_target

        # Create statistics dictionary
        stats = {
            'match_id': self.match_id,
            'team': self.team_name,
            'opponent': self.opponent or 'Unknown',
            'is_home': is_home,
            'match_datetime': datetime.datetime.now(),  # We would need to extract this from the page
            'shots': shots,
            'shots_on_target': shots_on_target,
            'goals': goals,
            'source': 'totalcorner'
        }

        self.results.append(stats)

    def parse_match_datetime(self, date_str):
        """
        Parse date and time string from TotalCorner format.

        Args:
            date_str: String in format "MM/DD HH:MM"

        Returns:
            datetime object or None if parsing fails
        """
        try:
            # Parse the date and time parts
            match = re.match(r"(\d{2})/(\d{2})\s+(\d{2}):(\d{2})", date_str.strip())
            if not match:
                return None

            month, day, hour, minute = map(int, match.groups())

            # Determine year (current or next year)
            current_date = datetime.datetime.now()
            year = current_date.year

            # If the month is earlier than current month, it's next year
            if month < current_date.month:
                year += 1

            # Create datetime object
            match_datetime = datetime.datetime(year, month, day, hour, minute)
            return match_datetime

        except Exception as e:
            self.logger.error(f"Error parsing date/time: {date_str}: {e}")
            return None