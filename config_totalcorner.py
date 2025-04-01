"""
Configuration settings for TotalCorner integration.
"""

# Base URL
TOTALCORNER_BASE_URL = "https://www.totalcorner.com"

# Team configuration with correct TotalCorner IDs
TOTALCORNER_TEAMS = [
    {"name": "Liverpool", "id": "2", "flashscore_id": "lId4TMwf"},
    {"name": "Manchester Utd", "id": "4", "flashscore_id": "ppjDR086"},
    {"name": "Manchester City", "id": "9", "flashscore_id": "Wtn9Stg0"},
    {"name": "Chelsea", "id": "16", "flashscore_id": "4fGZN2oK"},
    {"name": "Arsenal", "id": "1", "flashscore_id": "hA1Zm19f"},
    {"name": "Tottenham", "id": "6", "flashscore_id": "UDg08Ohm"},
    {"name": "Newcastle United", "id": "7", "flashscore_id": "p6ahwuwJ"},
    {"name": "Barcelona", "id": "235", "flashscore_id": "SKbpVP5K"},
    {"name": "Real Madrid", "id": "247", "flashscore_id": "W8mj7MDD"},
    {"name": "Atletico Madrid", "id": "241", "flashscore_id": "jaarqpLQ"},
    {"name": "Athletic Bilbao", "id": "128", "flashscore_id": "IP5zl0cJ"},
    {"name": "Bayern Munich", "id": "281", "flashscore_id": "nVp0wiqd"},
    {"name": "Bayer Leverkusen", "id": "125", "flashscore_id": "4jcj2zMd"},
    {"name": "RB Leipzig", "id": "297", "flashscore_id": "KbS1suSm"},
    {"name": "Dortmund", "id": "273", "flashscore_id": "nP1i5US1"},
    {"name": "Rangers", "id": "2455", "flashscore_id": "8vAWQXNS"},
    {"name": "Celtic", "id": "1371", "flashscore_id": "QFKRRD8M"}
]

# Collection delay configuration (in hours)
COLLECTION_DELAYS = {
    "default": 2.5,  # Default for domestic leagues
    "champions_league": 3.0,  # Champions League matches might need more time
    "cup": 3.5,  # Cup matches (potential extra time and penalties)
}

# TotalCorner XPath selectors for Scrapy
TOTALCORNER_SELECTORS = {
    "match_rows": "//tbody[@class='tbody_match']/tr",
    "match_datetime": "td[@class='text-center'][1]/text()",
    "home_team": "td[@class='text-right match_home']/a/span/text()",
    "away_team": "td[@class='text-left match_away']/a/span/text()",
    "match_details_link": "td[@class='text-center td_analysis']/a[contains(button/text(), 'Stats')]/@href",
    "match_score": "//div[@class='panel-body']/p/span[contains(text(), 'Score:')]/text()",
    "home_shots_on_target": "//div[@class='score-bar-item']/div[@class='row']/div[contains(text(), 'Shoot on target')]/preceding-sibling::div/text()",
    "away_shots_on_target": "//div[@class='score-bar-item']/div[@class='row']/div[contains(text(), 'Shoot on target')]/following-sibling::div/text()",
    "home_shots_off_target": "//div[@class='score-bar-item']/div[@class='row']/div[contains(text(), 'Shoot off target')]/preceding-sibling::div/text()",
    "away_shots_off_target": "//div[@class='score-bar-item']/div[@class='row']/div[contains(text(), 'Shoot off target')]/following-sibling::div/text()",
}

# Scrapy settings
SCRAPY_SETTINGS = {
    'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
    'ROBOTSTXT_OBEY': False,
    'DOWNLOAD_DELAY': 1,
    'COOKIES_ENABLED': True,
    'CONCURRENT_REQUESTS': 1,
    'RETRY_TIMES': 3,
    'RETRY_HTTP_CODES': [500, 502, 503, 504, 522, 524, 408, 429]
}