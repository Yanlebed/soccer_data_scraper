"""
Tests for TotalCorner Scrapy spider.
"""
import os
import sys
import unittest
from scrapy.http import TextResponse
from unittest.mock import patch, MagicMock

# Add parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper.totalcorner_spider import TotalCornerSpider

class TestTotalCornerSpider(unittest.TestCase):
    """Test cases for TotalCorner spider."""

    def setUp(self):
        """Set up test fixtures."""
        self.spider = TotalCornerSpider(team_id="235", team_name="Barcelona")

    def test_parse_match_datetime(self):
        """Test parsing match datetime."""
        # Test valid date
        result = self.spider.parse_match_datetime("04/05 21:00")
        self.assertIsNotNone(result)
        self.assertEqual(result.month, 4)
        self.assertEqual(result.day, 5)
        self.assertEqual(result.hour, 21)
        self.assertEqual(result.minute, 0)

        # Test invalid date
        result = self.spider.parse_match_datetime("Invalid date")
        self.assertIsNone(result)

    def test_start_requests(self):
        """Test start_requests method."""
        # Test with team_id and team_name
        self.spider.team_id = "235"
        self.spider.team_name = "Barcelona"
        requests = list(self.spider.start_requests())
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0].url, "https://www.totalcorner.com/team/view/235")
        self.assertEqual(requests[0].callback, self.spider.parse_upcoming_matches)