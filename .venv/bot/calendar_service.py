from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

class CalendarService:
    def __init__(self, service_account_file: str, calendar_id: str, scopes: list):
        self.service_account_file = service_account_file
        self.calendar_id = calendar_id
        self.scopes = scopes
        self.service = self._authenticate()

    def _authenticate(self):
        """Аутентификация в Google API"""
        try:
            credentials = service_account.Credentials.from_service_account_file(
                self.service_account_file,
                scopes=self.scopes
            )
            return build('calendar', 'v3', credentials=credentials)
        except Exception as e:
            logger.error(f"Auth error: {e}")
            raise

    async def get_events(self, max_results: int = 10):
        """Получение событий из календаря"""
        try:
            now = datetime.utcnow().isoformat() + 'Z'
            return self.service.events().list(
                calendarId=self.calendar_id,
                timeMin=now,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute().get('items', [])
        except Exception as e:
            logger.error(f"Calendar API error: {e}")
            return []