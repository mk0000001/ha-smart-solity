"""Async client for the private Smart Solity cloud API."""

from __future__ import annotations

import asyncio
import base64
from collections.abc import Awaitable, Callable
from datetime import date, datetime, time
import hashlib
from typing import Any
from urllib.parse import quote

from aiohttp import ClientError, ClientResponse, ClientSession

from .const import (
    API_BASE_URL,
    APP_SOURCE,
    COMMAND_CONNECT_GATEWAY,
    COMMAND_LOCK,
    COMMAND_SET_ONE_TIME_PIN,
    COMMAND_STATUS,
    COMMAND_UNLOCK,
    LANGUAGE,
)
from .models import SmartSolityDevice

TokenCallback = Callable[[str, str], Awaitable[None]]


class SmartSolityError(Exception):
    """Base Smart Solity error."""


class SmartSolityConnectionError(SmartSolityError):
    """The cloud could not be reached or returned malformed data."""


class SmartSolityAuthError(SmartSolityError):
    """Authentication failed or expired."""


class SmartSolityApiError(SmartSolityError):
    """The cloud rejected an otherwise valid request."""


class SmartSolityClient:
    """Small client matching the protocol used by Smart Solity Android 2.0.17."""

    def __init__(
        self,
        session: ClientSession,
        *,
        token: str = "",
        token_password: str = "",
        phone_token: str = "",
        email: str = "",
        member_name: str = "",
        token_callback: TokenCallback | None = None,
    ) -> None:
        self._session = session
        self.token = token
        self.token_password = token_password
        self.phone_token = phone_token
        self.email = email
        self.member_name = member_name
        self.member_id = ""
        self._token_callback = token_callback
        self._auth_lock = asyncio.Lock()

    @staticmethod
    def hash_password(password: str) -> str:
        """Return the exact SHA-256/Base64 value expected by the app API."""
        digest = hashlib.sha256(password.encode("utf-8")).digest()
        return base64.b64encode(digest).decode("ascii")

    async def async_login(self, email: str, password: str) -> dict[str, Any]:
        """Log in with account credentials and retain only issued tokens."""
        self.email = email
        contents = await self._request(
            "POST",
            "/api_v2/login",
            json={
                "emailId": email,
                "hashedPwd": self.hash_password(password),
                "phoneToken": self.phone_token,
                "appSource": APP_SOURCE,
                "lang": LANGUAGE,
            },
            authenticated=False,
        )
        if not isinstance(contents, dict) or contents.get("loginResult") != 0:
            raise SmartSolityAuthError("Invalid Smart Solity email or password")
        member = contents.get("memberInfo")
        if isinstance(member, dict):
            self.member_name = str(member.get("memberName") or "")
            self.member_id = str(member.get("memberId") or "")
            self.email = str(member.get("emailId") or email)
        if not self.token or not self.token_password:
            raise SmartSolityConnectionError("Login response did not include tokens")
        return contents

    async def async_refresh_tokens(self) -> None:
        """Rotate the token pair as the official app does at startup."""
        async with self._auth_lock:
            await self._request(
                "PUT",
                "/api_v2/login",
                json={"appSource": APP_SOURCE, "lang": LANGUAGE},
                retry_auth=False,
            )

    async def async_get_devices(self) -> dict[str, SmartSolityDevice]:
        """Return all door locks registered to the account."""
        contents = await self._request("GET", "/api_v2/myDevice")
        if not isinstance(contents, dict):
            raise SmartSolityConnectionError("Device response is not an object")
        raw_devices = contents.get("myDeviceList", [])
        if not isinstance(raw_devices, list):
            raise SmartSolityConnectionError("Device list is malformed")
        try:
            devices = [
                SmartSolityDevice.from_dict(item)
                for item in raw_devices
                if isinstance(item, dict)
            ]
        except ValueError as err:
            raise SmartSolityConnectionError(str(err)) from err
        return {device.device_id: device for device in devices}

    async def async_connect_gateway(self, device_id: str) -> None:
        """Ask the cloud gateway to keep its door-lock link active."""
        await self._control(device_id, COMMAND_CONNECT_GATEWAY, "120")

    async def async_request_status(self, device_id: str) -> None:
        """Request a fresh door-lock status from the gateway."""
        await self._control(device_id, COMMAND_STATUS, "")

    async def async_lock(self, device_id: str) -> None:
        """Lock a door."""
        await self._control(device_id, COMMAND_LOCK, "1")

    async def async_unlock(self, device_id: str) -> None:
        """Unlock a door."""
        await self._control(device_id, COMMAND_UNLOCK, "1")

    async def async_get_users(self, device_id: str) -> dict[str, Any]:
        """Return the user and credential slots visible to this account."""
        contents = await self._request(
            "GET", f"/api_v2/myDeviceUser/{quote(device_id, safe='')}"
        )
        if not isinstance(contents, dict):
            raise SmartSolityConnectionError("User response is not an object")
        return _without_secrets(contents)

    async def async_invite_user(
        self,
        device_id: str,
        *,
        name: str,
        phone_number: str,
        role: str,
    ) -> dict[str, Any]:
        """Invite a family member using the same payload as the mobile app."""
        auth_type = {"manager": "1", "member": "2"}[role]
        return await self._invite(
            {
                "inviteMyDeviceId": device_id,
                "inviteAuthType": auth_type,
                "invitePhoneName": name,
                "invitePhoneNumber": phone_number,
            }
        )

    async def async_create_guest_pin(
        self,
        device_id: str,
        *,
        pin: str,
        guest_name: str,
        phone_number: str,
        access_type: str,
        start_date: date,
        end_date: date,
        start_time: time,
        end_time: time,
        weekdays: list[str],
    ) -> dict[str, Any]:
        """Create a scheduled or one-time visitor PIN."""
        if access_type == "one_time":
            option = "/".join(
                (
                    pin,
                    start_date.strftime("%Y%m%d"),
                    end_date.strftime("%Y%m%d"),
                    start_time.strftime("%H:%M"),
                    end_time.strftime("%H:%M"),
                )
            )
            await self.async_connect_gateway(device_id)
            result = await self._control(device_id, COMMAND_SET_ONE_TIME_PIN, option)
            return _without_secrets(result) if isinstance(result, dict) else {}

        selected = set(weekdays)
        payload: dict[str, Any] = {
            "inviteMyDeviceId": device_id,
            "inviteAuthType": "3",
            "invitePhoneName": guest_name,
            "invitePhoneNumber": phone_number,
            "invitePassword": pin,
            "inviteNickname": "",
            "inviteStartDate": start_date.isoformat(),
            "inviteEndDate": end_date.isoformat(),
            "inviteStartTime": start_time.strftime("%H:%M"),
            "inviteEndTime": end_time.strftime("%H:%M"),
        }
        for field, day in (
            ("inviteMondayYn", "monday"),
            ("inviteTuesdayYn", "tuesday"),
            ("inviteWednesdayYn", "wednesday"),
            ("inviteThursdayYn", "thursday"),
            ("inviteFridayYn", "friday"),
            ("inviteSaturdayYn", "saturday"),
            ("inviteSundayYn", "sunday"),
        ):
            payload[field] = "Y" if access_type == "weekly" and day in selected else "N"
        return await self._invite(payload)

    async def async_get_access_log(
        self, device_id: str, *, limit: int = 20
    ) -> dict[str, Any]:
        """Return recent access events, matching the app's all-events view."""
        offset = datetime.now().astimezone().strftime("%z")
        timezone = f"{offset[:3]}:{offset[3:]}"
        contents = await self._request(
            "GET",
            f"/api_v2/retrieveLog/page/{quote(device_id, safe='')}",
            params={
                "pMemberId": "",
                "pLogType": "",
                "pLogStart": 0,
                "pLogLength": limit,
                "pTimezone": timezone,
            },
        )
        if not isinstance(contents, dict):
            raise SmartSolityConnectionError("Access log response is not an object")
        return _without_secrets(contents)

    async def _invite(self, item: dict[str, Any]) -> dict[str, Any]:
        item.update(
            {
                "appSource": APP_SOURCE,
                "lang": LANGUAGE,
                "inviteDt": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
        contents = await self._request(
            "POST", "/api_v2/invite", json={"inviteList": [item]}
        )
        if not isinstance(contents, dict):
            raise SmartSolityConnectionError("Invite response is not an object")
        return _without_secrets(contents)

    async def _control(
        self, device_id: str, command: str, option: str
    ) -> dict[str, Any] | None:
        contents = await self._request(
            "PUT",
            f"/api_v2/controlDevice/{quote(device_id, safe='')}",
            json={"controlType": command, "optionValue": option},
        )
        return contents if isinstance(contents, dict) else None

    async def _reissue_tokens(self) -> None:
        if not self.email or not self.member_name or not self.phone_token:
            raise SmartSolityAuthError("Session expired")
        contents = await self._request(
            "POST",
            "/api_v2/login/reissue",
            json={
                "emailId": self.email,
                "memberName": self.member_name,
                "phoneToken": self.phone_token,
                "appSource": APP_SOURCE,
                "lang": LANGUAGE,
            },
            retry_auth=False,
        )
        if not isinstance(contents, dict) or contents.get("loginResult") != 0:
            raise SmartSolityAuthError("Session could not be renewed")

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        authenticated: bool = True,
        retry_auth: bool = True,
    ) -> Any:
        headers = {"Connection": "close"}
        if authenticated:
            if not self.token or not self.token_password:
                raise SmartSolityAuthError("Authentication tokens are missing")
            headers.update(
                {"Authorization": self.token, "AuthorizationPwd": self.token_password}
            )
        try:
            async with asyncio.timeout(15):
                response = await self._session.request(
                    method,
                    f"{API_BASE_URL}{path}",
                    json=json,
                    params=params,
                    headers=headers,
                )
                async with response:
                    if response.status in (401, 403):
                        if authenticated and retry_auth:
                            async with self._auth_lock:
                                await self._reissue_tokens()
                            return await self._request(
                                method,
                                path,
                                json=json,
                                params=params,
                                authenticated=authenticated,
                                retry_auth=False,
                            )
                        raise SmartSolityAuthError("Smart Solity rejected authentication")
                    return await self._decode_response(response)
        except SmartSolityError:
            raise
        except (TimeoutError, ClientError) as err:
            raise SmartSolityConnectionError(f"Cloud request failed: {err}") from err

    async def _decode_response(self, response: ClientResponse) -> Any:
        if response.status >= 400:
            raise SmartSolityConnectionError(
                f"Smart Solity returned HTTP {response.status}"
            )
        try:
            payload = await response.json(content_type=None)
        except (ValueError, ClientError) as err:
            raise SmartSolityConnectionError("Cloud returned invalid JSON") from err
        if not isinstance(payload, dict):
            raise SmartSolityConnectionError("Cloud response is not an object")
        if payload.get("result") != 0:
            message = payload.get("errorMessage") or "Smart Solity request failed"
            raise SmartSolityApiError(str(message))
        contents = payload.get("contents")
        if isinstance(contents, dict):
            new_token = contents.get("token")
            new_password = contents.get("tokenPwd")
            changed = False
            if isinstance(new_token, str) and new_token:
                self.token = new_token
                changed = True
            if isinstance(new_password, str) and new_password:
                self.token_password = new_password
                changed = True
            if changed and self._token_callback is not None:
                await self._token_callback(self.token, self.token_password)
        return contents


def _without_secrets(value: Any) -> Any:
    """Remove credential values before returning data to Home Assistant."""
    if isinstance(value, list):
        return [_without_secrets(item) for item in value]
    if not isinstance(value, dict):
        return value
    return {
        key: _without_secrets(item)
        for key, item in value.items()
        if not any(part in key.casefold() for part in ("password", "pinvalue", "token"))
    }
