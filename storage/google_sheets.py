"""
Google Sheets integration for storing match statistics.
"""
import os
from typing import Dict, List, Optional

import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from gspread_dataframe import set_with_dataframe

from utils.logger import setup_logger

# Set up logger
logger = setup_logger(__name__)


class GoogleSheetsManager:
    """Handles Google Sheets operations."""

    def __init__(self, credentials_path: str = None, sheet_name: str = "Football Match Statistics"):
        """
        Initialize the Google Sheets manager.

        Args:
            credentials_path: Path to Google service account credentials JSON
            sheet_name: Name of the Google Sheet to use
        """
        self.credentials_path = credentials_path or os.environ.get("GOOGLE_CREDS_PATH")
        self.sheet_name = sheet_name or os.environ.get("GOOGLE_SHEET_NAME", "Football Match Statistics")
        self.client = None
        self.sheet = None
        self.stats_worksheet = None
        self.initialized = False

    def initialize(self) -> bool:
        """
        Initialize Google Sheets client if credentials are available.

        Returns:
            True if initialization successful, False otherwise
        """
        try:
            if not self.credentials_path:
                logger.warning("No Google credentials path provided")
                return False

            if not os.path.exists(self.credentials_path):
                logger.warning(f"Google credentials file not found at {self.credentials_path}")
                return False

            # Define the scope
            scope = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]

            # Get credentials
            creds = Credentials.from_service_account_file(self.credentials_path, scopes=scope)
            self.client = gspread.authorize(creds)

            # Check if the sheet exists, create if it doesn't
            try:
                self.sheet = self.client.open(self.sheet_name)
            except gspread.exceptions.SpreadsheetNotFound:
                self.sheet = self.client.create(self.sheet_name)
                # Share with owner's email (assuming it's in the credentials)
                service_account_info = creds.service_account_info
                if 'client_email' in service_account_info:
                    self.sheet.share(service_account_info['client_email'], role='writer', perm_type='user')
                logger.info(f"Created new Google Sheet: {self.sheet_name}")

            # Check if the stats worksheet exists
            try:
                self.stats_worksheet = self.sheet.worksheet("Match Statistics")
            except gspread.exceptions.WorksheetNotFound:
                self.stats_worksheet = self.sheet.add_worksheet(
                    title="Match Statistics",
                    rows=1000,
                    cols=8  # Added an extra column for source
                )
                # Add headers
                headers = ["Team", "Home Or Away", "Opponent", "Shots at Goal",
                          "Shots On Target", "Goals Scored", "Match Date", "Source"]
                self.stats_worksheet.append_row(headers)
                logger.info("Created new worksheet: Match Statistics")

            self.initialized = True
            logger.info("Google Sheets client initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Error initializing Google Sheets client: {e}")
            return False

    def update_match_statistics(self, stats_list: List) -> bool:
        """
        Update match statistics in Google Sheets.

        Args:
            stats_list: List of MatchStatistics objects

        Returns:
            True if update successful, False otherwise
        """
        if not stats_list:
            logger.warning("No statistics to update in Google Sheets")
            return False

        # Try to initialize if not already done
        if not self.initialized and not self.initialize():
            logger.error("Failed to initialize Google Sheets client. Skipping update.")
            return False

        try:
            # Convert stats objects to dicts for DataFrame
            rows = []
            for stat in stats_list:
                row_dict = {
                    "Team": stat.team,
                    "Home Or Away": "Home" if stat.is_home else "Away",
                    "Opponent": stat.opponent,
                    "Shots at Goal": stat.shots,
                    "Shots On Target": stat.shots_on_target,
                    "Goals Scored": stat.goals,
                    "Match Date": stat.match_datetime,
                    "Source": getattr(stat, "source", "totalcorner")
                }
                rows.append(row_dict)

            # Create DataFrame
            df = pd.DataFrame(rows)

            # Format datetime column
            if "Match Date" in df.columns:
                df["Match Date"] = pd.to_datetime(df["Match Date"]).dt.strftime('%Y-%m-%d %H:%M')

            # Select and order columns
            columns = ["Team", "Home Or Away", "Opponent", "Shots at Goal",
                      "Shots On Target", "Goals Scored", "Match Date", "Source"]
            df = df[columns]

            # Clear existing data (keeping headers)
            self.stats_worksheet.clear()
            self.stats_worksheet.append_row(columns)

            # Update the sheet
            set_with_dataframe(self.stats_worksheet, df)
            logger.info(f"Updated Google Sheet with {len(stats_list)} match statistics")
            return True

        except Exception as e:
            logger.error(f"Error updating Google Sheet: {e}")
            return False