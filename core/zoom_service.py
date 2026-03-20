"""
Zoom API Integration Service for Skillify.

Flow:
1. Learner books session
2. Django calls create_zoom_meeting()
3. Zoom API creates meeting → returns join_url, start_url, password
4. Links saved to Session model
5. Tutor sees start_url (host link), Learner sees join_url (participant link)

Setup Required:
1. Go to https://marketplace.zoom.us/
2. Create a "Server-to-Server OAuth" app
3. Copy Account ID, Client ID, Client Secret
4. Add to .env or settings.py:
   ZOOM_ACCOUNT_ID=xxx
   ZOOM_CLIENT_ID=xxx
   ZOOM_CLIENT_SECRET=xxx
"""

import requests
import base64
import logging
from datetime import datetime, timedelta
from django.conf import settings

logger = logging.getLogger(__name__)

# Token cache (in-memory, resets on server restart)
_token_cache = {
    'access_token': None,
    'expires_at': None,
}


def _get_zoom_access_token():
    """
    Get OAuth access token using Server-to-Server OAuth (Account Credentials).
    Tokens are cached until they expire.
    """
    # Return cached token if still valid
    if (_token_cache['access_token'] and _token_cache['expires_at']
            and datetime.now() < _token_cache['expires_at']):
        return _token_cache['access_token']

    account_id = getattr(settings, 'ZOOM_ACCOUNT_ID', '')
    client_id = getattr(settings, 'ZOOM_CLIENT_ID', '')
    client_secret = getattr(settings, 'ZOOM_CLIENT_SECRET', '')

    if not all([account_id, client_id, client_secret]):
        logger.warning('Zoom API credentials not configured. Set ZOOM_ACCOUNT_ID, ZOOM_CLIENT_ID, ZOOM_CLIENT_SECRET in settings.')
        return None

    # Base64 encode client_id:client_secret
    credentials = base64.b64encode(f'{client_id}:{client_secret}'.encode()).decode()

    try:
        response = requests.post(
            'https://zoom.us/oauth/token',
            headers={
                'Authorization': f'Basic {credentials}',
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            data={
                'grant_type': 'account_credentials',
                'account_id': account_id,
            },
            timeout=10,
        )

        if response.status_code == 200:
            data = response.json()
            _token_cache['access_token'] = data['access_token']
            # Expire 5 minutes early to be safe
            _token_cache['expires_at'] = datetime.now() + timedelta(seconds=data.get('expires_in', 3600) - 300)
            return data['access_token']
        else:
            logger.error(f'Zoom OAuth failed: {response.status_code} - {response.text}')
            return None

    except requests.RequestException as e:
        logger.error(f'Zoom OAuth request error: {e}')
        return None


def create_zoom_meeting(session):
    """
    Create a Zoom meeting for a Skillify session.

    Args:
        session: Session model instance (must have title, date, start_time, end_time)

    Returns:
        dict: {'success': True, 'meeting_id': ..., 'join_url': ..., 'start_url': ..., 'password': ...}
        or {'success': False, 'error': '...'}
    """
    access_token = _get_zoom_access_token()

    if not access_token:
        return {
            'success': False,
            'error': 'Zoom API not configured. Add ZOOM_ACCOUNT_ID, ZOOM_CLIENT_ID, ZOOM_CLIENT_SECRET to settings.',
        }

    # Calculate meeting duration in minutes
    start_dt = datetime.combine(session.date, session.start_time)
    end_dt = datetime.combine(session.date, session.end_time)
    duration_minutes = int((end_dt - start_dt).total_seconds() / 60)
    if duration_minutes <= 0:
        duration_minutes = 60  # Default 1 hour

    # Format start time for Zoom (ISO 8601)
    # Zoom expects: 2024-01-15T10:00:00
    start_time_str = start_dt.strftime('%Y-%m-%dT%H:%M:%S')

    # Meeting payload
    meeting_data = {
        'topic': f'Skillify: {session.title}',
        'type': 2,  # Scheduled meeting
        'start_time': start_time_str,
        'duration': duration_minutes,
        'timezone': getattr(settings, 'TIME_ZONE', 'Asia/Kolkata'),
        'agenda': session.description or f'Skillify session: {session.title}',
        'settings': {
            'host_video': True,
            'participant_video': True,
            'join_before_host': False,
            'mute_upon_entry': True,
            'watermark': False,
            'audio': 'both',
            'auto_recording': 'none',
            'waiting_room': True,
            'meeting_authentication': False,
        },
    }

    try:
        response = requests.post(
            'https://api.zoom.us/v2/users/me/meetings',
            headers={
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json',
            },
            json=meeting_data,
            timeout=15,
        )

        if response.status_code == 201:
            data = response.json()

            result = {
                'success': True,
                'meeting_id': str(data.get('id', '')),
                'join_url': data.get('join_url', ''),
                'start_url': data.get('start_url', ''),
                'password': data.get('password', ''),
            }

            logger.info(f'Zoom meeting created: {result["meeting_id"]} for session "{session.title}"')
            return result

        else:
            error_msg = f'Zoom API error {response.status_code}: {response.text}'
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}

    except requests.RequestException as e:
        error_msg = f'Zoom API request failed: {str(e)}'
        logger.error(error_msg)
        return {'success': False, 'error': error_msg}


def delete_zoom_meeting(meeting_id):
    """
    Delete a Zoom meeting (e.g., when session is cancelled).

    Args:
        meeting_id: Zoom meeting ID string

    Returns:
        bool: True if deleted successfully
    """
    if not meeting_id:
        return False

    access_token = _get_zoom_access_token()
    if not access_token:
        return False

    try:
        response = requests.delete(
            f'https://api.zoom.us/v2/meetings/{meeting_id}',
            headers={'Authorization': f'Bearer {access_token}'},
            timeout=10,
        )
        return response.status_code in (200, 204)

    except requests.RequestException as e:
        logger.error(f'Failed to delete Zoom meeting {meeting_id}: {e}')
        return False


def is_zoom_configured():
    """Check if Zoom API credentials are set in settings."""
    return all([
        getattr(settings, 'ZOOM_ACCOUNT_ID', ''),
        getattr(settings, 'ZOOM_CLIENT_ID', ''),
        getattr(settings, 'ZOOM_CLIENT_SECRET', ''),
    ])
