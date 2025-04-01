"""
DynamoDB operations for storing match schedules and statistics.
"""
import boto3
from datetime import datetime
from typing import Dict, List

from storage.database import DatabaseInterface
from models.match_data import MatchInfo, MatchStatistics
from utils.logger import setup_logger

# Set up logger
logger = setup_logger(__name__)


class DynamoDBManager(DatabaseInterface):
    """Handles DynamoDB operations for match data."""

    def __init__(self, matches_table='football_matches', stats_table='football_stats'):
        """
        Initialize the DynamoDB manager.

        Args:
            matches_table: Name of the table for match schedules
            stats_table: Name of the table for match statistics
        """
        self.dynamodb = boto3.resource('dynamodb')
        self.matches_table = self.dynamodb.Table(matches_table)
        self.stats_table = self.dynamodb.Table(stats_table)

    def save_scheduled_matches(self, matches: List[MatchInfo]) -> bool:
        """
        Save scheduled matches to DynamoDB.

        Args:
            matches: List of MatchInfo objects

        Returns:
            True if successful, False otherwise
        """
        if not matches:
            return True

        try:
            with self.matches_table.batch_writer() as batch:
                for match in matches:
                    batch.put_item(Item=self._serialize_match(match))

            logger.info(f"Saved {len(matches)} scheduled matches to DynamoDB")
            return True

        except Exception as e:
            logger.error(f"Error saving scheduled matches to DynamoDB: {e}")
            return False

    def save_match_statistics(self, stats: MatchStatistics) -> bool:
        """
        Save match statistics to DynamoDB.

        Args:
            stats: MatchStatistics object

        Returns:
            True if successful, False otherwise
        """
        try:
            self.stats_table.put_item(Item=self._serialize_stats(stats))
            logger.info(f"Saved statistics for match {stats.match_id} to DynamoDB")
            return True

        except Exception as e:
            logger.error(f"Error saving match statistics to DynamoDB: {e}")
            return False

    def get_all_match_statistics(self) -> List[MatchStatistics]:
        """
        Retrieve all match statistics from DynamoDB.

        Returns:
            List of MatchStatistics objects
        """
        try:
            response = self.stats_table.scan()
            items = response.get('Items', [])

            # Process paginated results if necessary
            while 'LastEvaluatedKey' in response:
                response = self.stats_table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
                items.extend(response.get('Items', []))

            # Convert items to MatchStatistics objects
            stats_list = [self._deserialize_stats(item) for item in items]
            return stats_list

        except Exception as e:
            logger.error(f"Error getting match statistics from DynamoDB: {e}")
            return []

    def get_upcoming_matches(self) -> List[MatchInfo]:
        """
        Retrieve upcoming matches from DynamoDB.

        Returns:
            List of MatchInfo objects
        """
        try:
            # Get current time in ISO format
            now = datetime.now().isoformat()

            # Create a FilterExpression for matches with collection_time > now
            response = self.matches_table.scan(
                FilterExpression='collection_time > :now',
                ExpressionAttributeValues={':now': now}
            )

            items = response.get('Items', [])

            # Process paginated results if necessary
            while 'LastEvaluatedKey' in response:
                response = self.matches_table.scan(
                    ExclusiveStartKey=response['LastEvaluatedKey'],
                    FilterExpression='collection_time > :now',
                    ExpressionAttributeValues={':now': now}
                )
                items.extend(response.get('Items', []))

            # Convert items to MatchInfo objects
            matches = [self._deserialize_match(item) for item in items]

            # Sort by match datetime
            matches.sort(key=lambda x: x.match_datetime)

            return matches

        except Exception as e:
            logger.error(f"Error getting upcoming matches from DynamoDB: {e}")
            return []

    def _serialize_match(self, match: MatchInfo) -> Dict:
        """
        Convert MatchInfo object to DynamoDB item.

        Args:
            match: MatchInfo object

        Returns:
            Dictionary suitable for DynamoDB
        """
        return {
            'match_id': match.match_id,
            'team': match.team,
            'opponent': match.opponent,
            'is_home': match.is_home,
            'match_datetime': match.match_datetime.isoformat(),
            'competition_type': match.competition_type,
            'collection_time': match.collection_time.isoformat() if match.collection_time else None,
            'stats_url': getattr(match, 'stats_url', None)
        }

    def _deserialize_match(self, item: Dict) -> MatchInfo:
        """
        Convert DynamoDB item to MatchInfo object.

        Args:
            item: DynamoDB item

        Returns:
            MatchInfo object
        """
        # Extract stats_url if present
        stats_url = item.pop('stats_url', None)

        # Convert ISO datetime strings to datetime objects
        if isinstance(item.get('match_datetime'), str):
            item['match_datetime'] = datetime.fromisoformat(item['match_datetime'])

        if isinstance(item.get('collection_time'), str) and item['collection_time']:
            item['collection_time'] = datetime.fromisoformat(item['collection_time'])

        # Create MatchInfo object
        match_info = MatchInfo(
            match_id=item['match_id'],
            team=item['team'],
            opponent=item['opponent'],
            is_home=item['is_home'],
            match_datetime=item['match_datetime'],
            competition_type=item.get('competition_type', 'default'),
            collection_time=item.get('collection_time')
        )

        # Set stats_url if it exists
        if stats_url:
            match_info.stats_url = stats_url

        return match_info

    def _serialize_stats(self, stats: MatchStatistics) -> Dict:
        """
        Convert MatchStatistics object to DynamoDB item.

        Args:
            stats: MatchStatistics object

        Returns:
            Dictionary suitable for DynamoDB
        """
        return {
            'match_id': stats.match_id,
            'team': stats.team,
            'opponent': stats.opponent,
            'is_home': stats.is_home,
            'match_datetime': stats.match_datetime.isoformat(),
            'collection_datetime': stats.collection_datetime.isoformat(),
            'shots': stats.shots,
            'shots_on_target': stats.shots_on_target,
            'goals': stats.goals,
            'source': getattr(stats, 'source', 'totalcorner')
        }

    def _deserialize_stats(self, item: Dict) -> MatchStatistics:
        """
        Convert DynamoDB item to MatchStatistics object.

        Args:
            item: DynamoDB item

        Returns:
            MatchStatistics object
        """
        # Convert ISO format strings to datetime objects
        if isinstance(item.get('match_datetime'), str):
            item['match_datetime'] = datetime.fromisoformat(item['match_datetime'])

        if isinstance(item.get('collection_datetime'), str):
            item['collection_datetime'] = datetime.fromisoformat(item['collection_datetime'])

        return MatchStatistics(
            match_id=item['match_id'],
            team=item['team'],
            opponent=item['opponent'],
            is_home=item['is_home'],
            match_datetime=item['match_datetime'],
            collection_datetime=item['collection_datetime'],
            shots=item.get('shots'),
            shots_on_target=item.get('shots_on_target'),
            goals=item.get('goals'),
            source=item.get('source', 'totalcorner')
        )