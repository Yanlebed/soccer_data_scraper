"""
Date and time utilities for the Totalcorner scraper.
"""
import datetime

def calculate_collection_time(match_time: datetime.datetime, 
                              competition_type: str = "default",
                              delays: dict = None) -> datetime.datetime:
    """
    Calculate when to collect match statistics based on match time and competition type.
    
    Args:
        match_time: Match start time
        competition_type: Type of competition (default, champions_league, cup)
        delays: Dictionary with delay hours by competition type
        
    Returns:
        datetime for when to collect statistics
    """
    if delays is None:
        delays = {
            "default": 2.5,
            "champions_league": 3.0,
            "cup": 3.5
        }
    
    delay_hours = delays.get(competition_type, delays["default"])
    return match_time + datetime.timedelta(hours=delay_hours)
