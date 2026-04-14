import os
from typing import Any

import httpx

from civicpulse.scraper.models import RawDocument

DEFAULT_CUSTOMER = "BA0924"


class ECodeGatewayClient:
    def __init__(self, api_key: str, api_secret: str, customer: str) -> None:
        self._customer = customer
        self._client = httpx.Client(
            base_url="https://api.ecodegateway.com",
            headers={"api-key": api_key, "api-secret": api_secret},
            timeout=20.0,
        )

    def get_structure(self, guid: str) -> dict[str, Any]:
        response = self._client.get(f"/customer/{self._customer}/structure/{guid}")
        response.raise_for_status()
        return response.json()

    def get_content(self, guid: str) -> str:
        response = self._client.get(f"/customer/{self._customer}/code/content/{guid}")
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, dict):
            return str(payload.get("content", ""))
        return str(payload)


class ECodeScraper:
    def __init__(
        self,
        *,
        api_client: ECodeGatewayClient | None = None,
        api_key: str | None = None,
        api_secret: str | None = None,
        customer: str | None = None,
    ) -> None:
        self.customer = customer or os.getenv("CIVICPULSE_ECODE_CUSTOMER", DEFAULT_CUSTOMER)
        resolved_api_key = api_key or os.getenv("CIVICPULSE_ECODE_API_KEY")
        resolved_api_secret = api_secret or os.getenv("CIVICPULSE_ECODE_API_SECRET")

        if api_client is None and (not resolved_api_key or not resolved_api_secret):
            raise RuntimeError("API key not configured for eCode360 API import.")

        self._api_client = api_client or ECodeGatewayClient(
            api_key=resolved_api_key or "",
            api_secret=resolved_api_secret or "",
            customer=self.customer,
        )

    def scrape_all(self) -> list[RawDocument]:
        docs: list[RawDocument] = []
        self._walk_structure("ROOT", docs)
        return docs

    def _walk_structure(self, guid: str, docs: list[RawDocument]) -> None:
        node = self._api_client.get_structure(guid)
        for child in node.get("children", []):
            if child.get("node_type") == "section":
                docs.append(self._section_to_document(child))
                continue
            child_guid = child.get("guid")
            if child_guid:
                self._walk_structure(child_guid, docs)

    def _section_to_document(self, section: dict[str, Any]) -> RawDocument:
        section_guid = str(section["guid"])
        section_number = str(section.get("section_number") or section.get("number") or "")
        title = str(section.get("title") or section_number or "Untitled")
        content = self._api_client.get_content(section_guid)
        return RawDocument(
            url=f"https://ecode360.com/{self.customer}#{section_number}" if section_number else f"https://ecode360.com/{self.customer}",
            content=f"§ {section_number}. {title}\n\n{content}".strip(),
            title=title,
            document_type="ordinance",
            date=None,
            meeting_id=None,
            extra_metadata={"section_number": section_number or None},
        )
