"""Official Google authorization-code/PKCE adapter and encrypted token storage."""

import base64
import hashlib
import json
import os
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

import httpx
from cryptography.fernet import Fernet, InvalidToken

SCOPES = "openid email https://www.googleapis.com/auth/calendar.events.readonly"


class CalendarFailure(Exception):
    """Safe, deliberately non-provider-specific error boundary."""


class CalendarRevoked(CalendarFailure):
    pass


class SyncExpired(CalendarFailure):
    pass


class Vault:
    def __init__(self, settings):
        self.settings = settings

    def cipher(self):
        raw = self.settings.calendar_encryption_key.get_secret_value().encode()
        if not raw:
            path = self.settings.calendar_key_file
            path.parent.mkdir(parents=True, exist_ok=True)
            try:
                fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            except FileExistsError:
                raw = path.read_bytes()
            else:
                raw = Fernet.generate_key()
                with os.fdopen(fd, "wb") as stream:
                    stream.write(raw)
        return Fernet(raw)

    def seal(self, value):
        return self.cipher().encrypt(json.dumps(value).encode()).decode()

    def open(self, value):
        try:
            return json.loads(self.cipher().decrypt(value.encode()))
        except (InvalidToken, ValueError, OSError):
            raise CalendarFailure(
                "Calendar credentials cannot be opened. Reconnect your calendar."
            ) from None


def challenge(verifier):
    return (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
        .rstrip(b"=")
        .decode()
    )


class GoogleCalendar:
    def __init__(self, settings):
        self.settings = settings

    def authorization_url(self, state, verifier):
        return "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(
            {
                "client_id": self.settings.google_client_id,
                "redirect_uri": self.settings.google_redirect_uri,
                "response_type": "code",
                "scope": SCOPES,
                "state": state,
                "code_challenge": challenge(verifier),
                "code_challenge_method": "S256",
                "access_type": "offline",
                "prompt": "consent",
                "include_granted_scopes": "true",
            }
        )

    def token(self, values):
        values = {
            **values,
            "client_id": self.settings.google_client_id,
            "client_secret": self.settings.google_client_secret.get_secret_value(),
        }
        try:
            with httpx.Client(timeout=20, follow_redirects=False) as client:
                response = client.post(
                    "https://oauth2.googleapis.com/token", data=values
                )
            if response.status_code == 400:
                raise CalendarRevoked(
                    "Calendar authorization expired. Reconnect your calendar."
                )
            response.raise_for_status()
            result = response.json()
            if not result.get("access_token"):
                raise ValueError()
            result["expires_at"] = (
                datetime.now(UTC)
                + timedelta(seconds=int(result.get("expires_in", 3600)))
            ).isoformat()
            return result
        except (httpx.HTTPError, ValueError, KeyError):
            raise CalendarFailure(
                "Google Calendar is temporarily unavailable. Please retry."
            ) from None

    def exchange(self, code, verifier):
        result = self.token(
            {
                "grant_type": "authorization_code",
                "code": code,
                "code_verifier": verifier,
                "redirect_uri": self.settings.google_redirect_uri,
            }
        )
        if (
            "https://www.googleapis.com/auth/calendar.events.readonly"
            not in result.get("scope", "").split()
        ):
            raise CalendarFailure("Read-only calendar permission was not granted.")
        if not result.get("refresh_token"):
            raise CalendarFailure(
                "Offline calendar permission was not granted. Reconnect with consent."
            )
        return result

    def refresh(self, credentials):
        result = self.token(
            {
                "grant_type": "refresh_token",
                "refresh_token": credentials["refresh_token"],
            }
        )
        return {**credentials, **result}

    def get(self, path, token, params=None):
        try:
            with httpx.Client(timeout=20, follow_redirects=False) as client:
                response = client.get(
                    path, headers={"Authorization": "Bearer " + token}, params=params
                )
            if response.status_code in (401, 403):
                raise CalendarRevoked(
                    "Calendar access needs attention. Reconnect your calendar."
                )
            if response.status_code == 410:
                raise SyncExpired()
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError):
            raise CalendarFailure(
                "Calendar synchronization failed. Please retry."
            ) from None

    def email(self, credentials):
        return self.get(
            "https://openidconnect.googleapis.com/v1/userinfo",
            credentials["access_token"],
        ).get("email", "")[:254]

    def events(self, credentials, sync_token, start, end):
        params = {
            "singleEvents": "true",
            "showDeleted": "true",
            "maxResults": 250,
            "fields": "items(id,status,summary,start,end,updated,recurringEventId,visibility,transparency),nextPageToken,nextSyncToken,timeZone",
        }
        if sync_token:
            params["syncToken"] = sync_token
        else:
            params.update(timeMin=start, timeMax=end)
        items = []
        for _ in range(20):
            result = self.get(
                "https://www.googleapis.com/calendar/v3/calendars/primary/events",
                credentials["access_token"],
                params,
            )
            items.extend(result.get("items", []))
            if not result.get("nextPageToken"):
                return items, result.get("nextSyncToken"), result.get("timeZone", "UTC")
            params["pageToken"] = result["nextPageToken"]
        raise CalendarFailure(
            "The calendar is too large to synchronize safely. Please use a smaller primary calendar."
        )

    def event(self, credentials, event_id):
        from urllib.parse import quote

        return self.get(
            "https://www.googleapis.com/calendar/v3/calendars/primary/events/"
            + quote(event_id, safe=""),
            credentials["access_token"],
            {
                "fields": "id,status,summary,start,end,updated,recurringEventId,visibility,transparency"
            },
        )

    def revoke(self, credentials):
        try:
            with httpx.Client(timeout=10) as client:
                client.post(
                    "https://oauth2.googleapis.com/revoke",
                    data={
                        "token": credentials.get(
                            "refresh_token", credentials.get("access_token", "")
                        )
                    },
                )
        except httpx.HTTPError:
            pass  # Local deletion always succeeds; Google Account permissions can also revoke.
