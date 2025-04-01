"""
Data models for matches and statistics.
"""
import datetime
from dataclasses import dataclass, field
from typing import Dict, Optional, Union


@dataclass
class MatchInfo:
    """
    Information about an upcoming match.
    """
    match_id: str
    team: str
    opponent: str
    is_home: bool
    match_datetime: datetime.datetime
    competition_type: str = "default"
    collection_time: Optional[datetime.datetime] = None
    stats_url: Optional[str] = None  # Added for TotalCorner integration

    def to_dict(self) -> Dict[str, Union[str, bool, datetime.datetime]]:
        """Convert to dictionary for database storage."""
        return {
            "match_id": self.match_id,
            "team": self.team,
            "opponent": self.opponent,
            "is_home": self.is_home,
            "match_datetime": self.match_datetime.isoformat(),
            "competition_type": self.competition_type,
            "collection_time": self.collection_time.isoformat() if self.collection_time else None,
            "stats_url": self.stats_url  # Include stats_url in the dictionary
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Union[str, bool, datetime.datetime]]) -> "MatchInfo":
        """Create from dictionary data."""
        # Convert ISO format strings back to datetime objects
        if isinstance(data.get("match_datetime"), str):
            data["match_datetime"] = datetime.datetime.fromisoformat(data["match_datetime"])

        if isinstance(data.get("collection_time"), str) and data["collection_time"]:
            data["collection_time"] = datetime.datetime.fromisoformat(data["collection_time"])

        # Extract stats_url if present
        stats_url = data.pop("stats_url", None)

        match_info = cls(**data)

        # Set stats_url if it exists
        if stats_url:
            match_info.stats_url = stats_url

        return match_info


@dataclass
class MatchStatistics:
    """
    Statistics for a completed match.
    """
    match_id: str
    team: str
    opponent: str
    is_home: bool
    match_datetime: datetime.datetime
    collection_datetime: datetime.datetime = field(default_factory=datetime.datetime.now)
    shots: Optional[int] = None
    shots_on_target: Optional[int] = None
    goals: Optional[int] = None
    source: str = "totalcorner"  # Added to track data source

    def to_dict(self) -> Dict[str, Union[str, bool, int, datetime.datetime]]:
        """Convert to dictionary for database storage."""
        return {
            "match_id": self.match_id,
            "team": self.team,
            "opponent": self.opponent,
            "is_home": self.is_home,
            "match_datetime": self.match_datetime.isoformat(),
            "collection_datetime": self.collection_datetime.isoformat(),
            "shots": self.shots,
            "shots_on_target": self.shots_on_target,
            "goals": self.goals,
            "source": self.source
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Union[str, bool, int, datetime.datetime]]) -> "MatchStatistics":
        """Create from dictionary data."""
        # Convert ISO format strings back to datetime objects
        if isinstance(data.get("match_datetime"), str):
            data["match_datetime"] = datetime.datetime.fromisoformat(data["match_datetime"])

        if isinstance(data.get("collection_datetime"), str):
            data["collection_datetime"] = datetime.datetime.fromisoformat(data["collection_datetime"])

        return cls(**data)

    def to_sheet_row(self) -> Dict[str, Union[str, int]]:
        """Convert to a row for Google Sheets."""
        return {
            "Team": self.team,
            "Home Or Away": "Home" if self.is_home else "Away",
            "Opponent": self.opponent,
            "Shots at Goal": self.shots,
            "Shots On Target": self.shots_on_target,
            "Goals Scored": self.goals,
            "Match Date": self.match_datetime,
            "Source": self.source
        }