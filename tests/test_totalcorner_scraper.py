"""
Tests for TotalCorner Scrapy spider.
"""
import os
import sys
import unittest
import datetime
from unittest.mock import patch, MagicMock
from scrapy.http import TextResponse, Request

# Add parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper.totalcorner_spider import TotalCornerSpider
from config_totalcorner import TOTALCORNER_BASE_URL

class TestTotalCornerSpider(unittest.TestCase):
    """Test cases for TotalCorner spider."""

    def setUp(self):
        """Set up test fixtures."""
        self.spider = TotalCornerSpider(team_id="235", team_name="Barcelona")
        self.logger = MagicMock()

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
        self.assertEqual(requests[0].url, f"{TOTALCORNER_BASE_URL}/team/view/235")
        self.assertEqual(requests[0].callback, self.spider.parse_upcoming_matches)

        # Test with match_id
        self.spider.team_id = None
        self.spider.match_id = "12345"
        requests = list(self.spider.start_requests())
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0].url, f"{TOTALCORNER_BASE_URL}/stats/12345")
        self.assertEqual(requests[0].callback, self.spider.parse_match_statistics)

        # Test with stats_url
        self.spider.match_id = None
        self.spider.stats_url = f"{TOTALCORNER_BASE_URL}/stats/12345"
        requests = list(self.spider.start_requests())
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0].url, f"{TOTALCORNER_BASE_URL}/stats/12345")
        self.assertEqual(requests[0].callback, self.spider.parse_match_statistics)

    def test_parse_upcoming_matches(self):
        """Test parsing upcoming matches."""
        # Create a mock response with sample HTML
        html = """
        <tbody class="tbody_match">
            <tr>
                <td class="text-center">04/05 21:00</td>
                <td class="text-right match_home"><a href="#"><span>Barcelona</span></a></td>
                <td class="text-left match_away"><a href="#"><span>Real Madrid</span></a></td>
                <td class="text-center td_analysis"><a href="/stats/12345"><button>Stats</button></a></td>
            </tr>
            <tr>
                <td class="text-center">04/08 19:00</td>
                <td class="text-right match_home"><a href="#"><span>Atletico Madrid</span></a></td>
                <td class="text-left match_away"><a href="#"><span>Barcelona</span></a></td>
                <td class="text-center td_analysis"><a href="/stats/67890"><button>Stats</button></a></td>
            </tr>
        </tbody>
        """

        # Create mock response
        response = TextResponse(
            url=f"{TOTALCORNER_BASE_URL}/team/view/235",
            body=html.encode('utf-8'),
            encoding='utf-8',
            request=Request(url=f"{TOTALCORNER_BASE_URL}/team/view/235")
        )

        # Set up future datetime patch to ensure matches are always in the future
        future_date = datetime.datetime.now() + datetime.timedelta(days=10)
        with patch.object(self.spider, 'parse_match_datetime', return_value=future_date):
            # Parse response
            self.spider.parse_upcoming_matches(response)

            # Check results
            self.assertEqual(len(self.spider.results), 2)

            # Check first match details (Barcelona vs Real Madrid)
            match1 = self.spider.results[0]
            self.assertEqual(match1['match_id'], '12345')
            self.assertEqual(match1['team'], 'Barcelona')
            self.assertEqual(match1['opponent'], 'Real Madrid')
            self.assertTrue(match1['is_home'])
            self.assertEqual(match1['match_datetime'], future_date)
            self.assertEqual(match1['stats_url'], f"{TOTALCORNER_BASE_URL}/stats/12345")

            # Check second match details (Atletico Madrid vs Barcelona)
            match2 = self.spider.results[1]
            self.assertEqual(match2['match_id'], '67890')
            self.assertEqual(match2['team'], 'Barcelona')
            self.assertEqual(match2['opponent'], 'Atletico Madrid')
            self.assertFalse(match2['is_home'])
            self.assertEqual(match2['match_datetime'], future_date)
            self.assertEqual(match2['stats_url'], f"{TOTALCORNER_BASE_URL}/stats/67890")

    def test_parse_match_statistics(self):
        """Test parsing match statistics."""
        # Create a mock response with sample HTML
        html = """
        <div class="panel-body">
            <p><span>Score: 2 - 1</span></p>
        </div>
        <div class="score-bar-item">
            <div class="row">
                <div>5</div>
                <div>Shoot on target</div>
                <div>3</div>
            </div>
        </div>
        <div class="score-bar-item">
            <div class="row">
                <div>7</div>
                <div>Shoot off target</div>
                <div>4</div>
            </div>
        </div>
        """

        # Create mock response
        response = TextResponse(
            url=f"{TOTALCORNER_BASE_URL}/stats/12345",
            body=html.encode('utf-8'),
            encoding='utf-8',
            request=Request(url=f"{TOTALCORNER_BASE_URL}/stats/12345")
        )

        # Test for home team
        self.spider.match_id = '12345'
        self.spider.team_name = 'Barcelona'
        self.spider.opponent = 'Real Madrid'
        self.spider.is_home = True

        self.spider.parse_match_statistics(response)

        # Check results for home team
        self.assertEqual(len(self.spider.results), 1)
        stats_home = self.spider.results[0]
        self.assertEqual(stats_home['match_id'], '12345')
        self.assertEqual(stats_home['team'], 'Barcelona')
        self.assertEqual(stats_home['opponent'], 'Real Madrid')
        self.assertTrue(stats_home['is_home'])
        self.assertEqual(stats_home['shots'], 12)  # 5 on target + 7 off target
        self.assertEqual(stats_home['shots_on_target'], 5)
        self.assertEqual(stats_home['goals'], 2)
        self.assertEqual(stats_home['source'], 'totalcorner')

        # Clear results and test for away team
        self.spider.results = []
        self.spider.is_home = False

        self.spider.parse_match_statistics(response)

        # Check results for away team
        self.assertEqual(len(self.spider.results), 1)
        stats_away = self.spider.results[0]
        self.assertEqual(stats_away['match_id'], '12345')
        self.assertEqual(stats_away['team'], 'Barcelona')
        self.assertEqual(stats_away['opponent'], 'Real Madrid')
        self.assertFalse(stats_away['is_home'])
        self.assertEqual(stats_away['shots'], 7)  # 3 on target + 4 off target
        self.assertEqual(stats_away['shots_on_target'], 3)
        self.assertEqual(stats_away['goals'], 1)
        self.assertEqual(stats_away['source'], 'totalcorner')

if __name__ == '__main__':
    unittest.main()