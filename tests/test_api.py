"""Protocol-level tests that do not require a Home Assistant installation."""

from __future__ import annotations

import asyncio
from datetime import date, time
from enum import StrEnum
import importlib.util
from pathlib import Path
import sys
from types import ModuleType
import unittest
from typing import Any


COMPONENT = Path(__file__).parents[1] / "custom_components" / "smart_solity"
package = ModuleType("smart_solity")
package.__path__ = [str(COMPONENT)]
sys.modules["smart_solity"] = package

homeassistant = ModuleType("homeassistant")
ha_const = ModuleType("homeassistant.const")


class Platform(StrEnum):
    LOCK = "lock"
    SENSOR = "sensor"


ha_const.Platform = Platform
sys.modules.setdefault("homeassistant", homeassistant)
sys.modules.setdefault("homeassistant.const", ha_const)

# The client only needs aiohttp's interfaces; the tests provide an in-memory
# session and therefore keep this test suite dependency-free.
aiohttp = ModuleType("aiohttp")
aiohttp.ClientError = type("ClientError", (Exception,), {})
aiohttp.ClientResponse = object
aiohttp.ClientSession = object
sys.modules.setdefault("aiohttp", aiohttp)


def _load(name: str):
    spec = importlib.util.spec_from_file_location(
        f"smart_solity.{name}", COMPONENT / f"{name}.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_load("const")
models = _load("models")
api = _load("api")


class FakeResponse:
    def __init__(self, status: int, payload: dict[str, Any]) -> None:
        self.status = status
        self._payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def json(self, *, content_type: object = None) -> dict[str, Any]:
        return self._payload


class FakeSession:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, str, dict[str, Any]]] = []

    async def request(self, method: str, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append((method, url, kwargs))
        return self.responses.pop(0)


def response(contents: Any) -> FakeResponse:
    return FakeResponse(200, {"result": 0, "errorMessage": "", "contents": contents})


class SmartSolityApiTests(unittest.IsolatedAsyncioTestCase):
    def test_password_hash_matches_android_algorithm(self) -> None:
        self.assertEqual(
            api.SmartSolityClient.hash_password("password"),
            "XohImNooBHFR0OVvjcYpJ3NgPQ1qq73WKhHvch0VQtg=",
        )

    async def test_login_does_not_retain_password_and_discovers_device(self) -> None:
        session = FakeSession(
            [
                response(
                    {
                        "loginResult": 0,
                        "token": "issued-token",
                        "tokenPwd": "issued-secret",
                        "memberInfo": {
                            "memberId": "member-1",
                            "memberName": "Test user",
                            "emailId": "user@example.com",
                        },
                    }
                ),
                response(
                    {
                        "myDeviceListCount": 1,
                        "myDeviceList": [
                            {
                                "myDeviceId": "lock-1",
                                "myDeviceNickName": "Front door",
                                "lockerStatus": "0",
                                "battery": 86,
                                "myDeviceMakerName": "Solity",
                                "myDeviceModelName": "Test lock",
                            }
                        ],
                    }
                ),
            ]
        )
        client = api.SmartSolityClient(session, phone_token="0123456789abcdef")
        await client.async_login("user@example.com", "password")
        devices = await client.async_get_devices()

        self.assertEqual(client.token, "issued-token")
        self.assertFalse(hasattr(client, "password"))
        self.assertTrue(devices["lock-1"].status == "0")
        login_json = session.calls[0][2]["json"]
        self.assertNotEqual(login_json["hashedPwd"], "password")
        self.assertNotIn("password", login_json)

    async def test_lock_control_payloads_match_mobile_app(self) -> None:
        session = FakeSession([response({}), response({}), response({})])
        client = api.SmartSolityClient(
            session, token="token", token_password="secret"
        )
        await client.async_connect_gateway("lock/1")
        await client.async_unlock("lock/1")
        await client.async_lock("lock/1")

        self.assertEqual(
            [call[2]["json"] for call in session.calls],
            [
                {"controlType": "connect_gateway", "optionValue": "120"},
                {"controlType": "open", "optionValue": "1"},
                {"controlType": "close", "optionValue": "1"},
            ],
        )
        self.assertTrue(all("lock%2F1" in call[1] for call in session.calls))

    async def test_unauthorized_request_reissues_tokens_once(self) -> None:
        session = FakeSession(
            [
                FakeResponse(401, {}),
                response(
                    {
                        "loginResult": 0,
                        "token": "new-token",
                        "tokenPwd": "new-secret",
                        "memberInfo": {},
                    }
                ),
                response({"myDeviceList": [], "myDeviceListCount": 0}),
            ]
        )
        client = api.SmartSolityClient(
            session,
            token="old-token",
            token_password="old-secret",
            phone_token="phone-token",
            email="user@example.com",
            member_name="Test user",
        )
        devices = await asyncio.wait_for(client.async_get_devices(), timeout=1)

        self.assertEqual(devices, {})
        self.assertEqual(client.token, "new-token")
        self.assertEqual(session.calls[1][0], "POST")
        self.assertTrue(session.calls[1][1].endswith("/api_v2/login/reissue"))

    async def test_startup_refresh_reissues_expired_tokens(self) -> None:
        session = FakeSession(
            [
                FakeResponse(401, {}),
                response(
                    {
                        "loginResult": 0,
                        "token": "renewed-token",
                        "tokenPwd": "renewed-secret",
                        "memberInfo": {},
                    }
                ),
                response({"loginResult": 0}),
            ]
        )
        stored: list[tuple[str, str]] = []

        async def store_tokens(token: str, token_password: str) -> None:
            stored.append((token, token_password))

        client = api.SmartSolityClient(
            session,
            token="expired-token",
            token_password="expired-secret",
            phone_token="local-device-id",
            email="user@example.com",
            member_name="Test user",
            token_callback=store_tokens,
        )

        await asyncio.wait_for(client.async_refresh_tokens(), timeout=1)

        self.assertEqual(
            [call[1].rsplit("/api_v2", 1)[-1] for call in session.calls],
            ["/login", "/login/reissue", "/login"],
        )
        self.assertEqual(stored, [("renewed-token", "renewed-secret")])

    async def test_family_invite_matches_mobile_app_payload(self) -> None:
        session = FakeSession([response({"inviteReturnList": []})])
        client = api.SmartSolityClient(
            session, token="token", token_password="secret"
        )

        await client.async_invite_user(
            "lock-1", name="Family", phone_number="01012345678", role="member"
        )

        item = session.calls[0][2]["json"]["inviteList"][0]
        self.assertEqual(session.calls[0][0], "POST")
        self.assertTrue(session.calls[0][1].endswith("/api_v2/invite"))
        self.assertEqual(item["inviteMyDeviceId"], "lock-1")
        self.assertEqual(item["inviteAuthType"], "2")
        self.assertEqual(item["invitePhoneNumber"], "01012345678")

    async def test_weekly_guest_pin_payload_and_response_are_redacted(self) -> None:
        session = FakeSession(
            [response({"invitePassword": "1234", "inviteReturnList": []})]
        )
        client = api.SmartSolityClient(
            session, token="token", token_password="secret"
        )

        result = await client.async_create_guest_pin(
            "lock-1",
            pin="1234",
            guest_name="Guest",
            phone_number="01012345678",
            access_type="weekly",
            start_date=date(2026, 8, 15),
            end_date=date(2026, 9, 15),
            start_time=time(9, 0),
            end_time=time(18, 0),
            weekdays=["monday", "friday"],
        )

        item = session.calls[0][2]["json"]["inviteList"][0]
        self.assertEqual(item["invitePassword"], "1234")
        self.assertEqual(item["inviteMondayYn"], "Y")
        self.assertEqual(item["inviteFridayYn"], "Y")
        self.assertEqual(item["inviteTuesdayYn"], "N")
        self.assertNotIn("invitePassword", result)

    async def test_one_time_pin_uses_gateway_and_set_one_pwd(self) -> None:
        session = FakeSession([response({}), response({"controlDeviceResult": 0})])
        client = api.SmartSolityClient(
            session, token="token", token_password="secret"
        )

        await client.async_create_guest_pin(
            "lock-1",
            pin="5678",
            guest_name="Guest",
            phone_number="01012345678",
            access_type="one_time",
            start_date=date(2026, 8, 15),
            end_date=date(2026, 8, 15),
            start_time=time(9, 0),
            end_time=time(10, 0),
            weekdays=[],
        )

        self.assertEqual(
            [call[2]["json"]["controlType"] for call in session.calls],
            ["connect_gateway", "set_one_pwd"],
        )
        self.assertEqual(
            session.calls[1][2]["json"]["optionValue"],
            "5678/20260815/20260815/09:00/10:00",
        )

    async def test_get_users_and_access_log_hide_credentials(self) -> None:
        session = FakeSession(
            [
                response(
                    {
                        "myDeviceUserList": [
                            {"myDeviceUserMemberName": "Guest", "pinValue": "4321"}
                        ]
                    }
                ),
                response({"retrieveLogList": [{"logMessage": "Opened"}]}),
            ]
        )
        client = api.SmartSolityClient(
            session, token="token", token_password="secret"
        )

        users = await client.async_get_users("lock-1")
        logs = await client.async_get_access_log("lock-1", limit=10)

        self.assertNotIn("pinValue", users["myDeviceUserList"][0])
        self.assertEqual(logs["retrieveLogList"][0]["logMessage"], "Opened")
        self.assertEqual(session.calls[1][2]["params"]["pLogLength"], 10)


if __name__ == "__main__":
    unittest.main()
