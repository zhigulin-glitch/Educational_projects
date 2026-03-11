from __future__ import annotations

import aiohttp


class ExternalAPIClient:
    def __init__(self, base_url: str, timeout: int = 10):
        self.base_url = base_url
        self.timeout = aiohttp.ClientTimeout(total=timeout)

    async def send_application(self, payload: dict) -> tuple[bool, str]:
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(self.base_url, json=payload) as response:
                    text = await response.text()
                    return response.status < 400, f'{response.status}: {text[:500]}'
        except Exception as exc:  # noqa: BLE001
            return False, str(exc)
