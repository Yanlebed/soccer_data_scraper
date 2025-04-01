"""
Database interface for storing match data.
"""
from abc import ABC, abstractmethod
from typing import List

from models.match_data import MatchInfo, MatchStatistics

class DatabaseInterface(ABC):
    """Abstract database interface for match data storage."""

    @abstractmethod
    def save_scheduled_matches(self, matches: List[MatchInfo]) -> bool:
        """Save scheduled matches to the database."""
        pass

    @abstractmethod
    def save_match_statistics(self, stats: MatchStatistics) -> bool:
        """Save match statistics to the database."""
        pass

    @abstractmethod
    def get_all_match_statistics(self) -> List[MatchStatistics]:
        """Retrieve all match statistics from the database."""
        pass

    @abstractmethod
    def get_upcoming_matches(self) -> List[MatchInfo]:
        """Retrieve upcoming matches from the database."""
        pass

# Default database implementation - can be set at runtime
database_instance = None

def get_database():
    """Get the current database instance."""
    if database_instance is None:
        raise RuntimeError("Database not initialized")
    return database_instance

def set_database(db_instance):
    """Set the current database instance."""
    global database_instance
    database_instance = db_instance