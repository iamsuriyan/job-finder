"""Unit tests for the founding team email discovery engine."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import respx

from fundwatch.email_finder import (
    clean_domain,
    discover_founding_team_emails,
    extract_company_name,
    extract_founders_from_text,
    generate_founder_emails,
    is_port_25_accessible,
    query_hunter_api,
    resolve_company_domain,
    verify_mx,
    verify_smtp_probe,
)
from fundwatch.models import Article, Extraction
from fundwatch.notifiers import format_article_message


def test_clean_domain() -> None:
    assert clean_domain("https://www.cognition.ai/about") == "cognition.ai"
    assert clean_domain("http://bobabhai.com:8080") == "bobabhai.com"
    assert clean_domain("satsure.co/") == "satsure.co"
    assert clean_domain("https://techcrunch.com/2026/01/01/sample") is None  # news outlet ignored
    assert clean_domain("invalid-domain") is None
    assert clean_domain(None) is None


def test_extract_founders_from_text() -> None:
    text1 = "Fintech platform PayQuick raises $10M. Founded by Scott Wu and Gaurav Luthra."
    founders1 = extract_founders_from_text(text1)
    names1 = [f["name"] for f in founders1]
    assert "Scott Wu" in names1
    assert "Gaurav Luthra" in names1

    text2 = "Robotics company BotCo, founded by Jane Smith, secures fresh funding."
    founders2 = extract_founders_from_text(text2)
    assert any(f["name"] == "Jane Smith" for f in founders2)

    text3 = "Co-founder and CEO Prateep Basu announced the closing of their Series B round."
    founders3 = extract_founders_from_text(text3)
    assert any(f["name"] == "Prateep Basu" for f in founders3)


def test_generate_founder_emails() -> None:
    emails = generate_founder_emails("Scott Wu", "cognition.ai")
    assert "scott@cognition.ai" in emails
    assert "scott.wu@cognition.ai" in emails
    assert "scottwu@cognition.ai" in emails
    assert "swu@cognition.ai" in emails

    single_name_emails = generate_founder_emails("Cher", "music.com")
    assert single_name_emails == ["cher@music.com"]


@patch("dns.resolver.resolve")
def test_verify_mx(mock_resolve: MagicMock) -> None:
    # Successful Google Workspace MX
    mock_item = MagicMock()
    mock_item.exchange = "aspmx.l.google.com."
    mock_resolve.return_value = [mock_item]

    has_mx, provider, hosts = verify_mx("example.com")
    assert has_mx is True
    assert provider == "Google Workspace"
    assert "aspmx.l.google.com" in hosts

    # Domain with no MX
    mock_resolve.side_effect = Exception("No answer")
    has_mx_fail, _, _ = verify_mx("bad.domain")
    assert has_mx_fail is False


@respx.mock
def test_resolve_company_domain_clearbit() -> None:
    respx.get("https://autocomplete.clearbit.com/v1/companies/suggest?query=SatSure").mock(
        return_value=httpx.Response(200, json=[{"name": "SatSure", "domain": "satsure.co"}])
    )

    with patch(
        "fundwatch.email_finder.verify_mx", return_value=(True, "Google", ["aspmx.google.com"])
    ):
        domain = resolve_company_domain("SatSure", article_text="")
        assert domain == "satsure.co"


@respx.mock
def test_query_hunter_api() -> None:
    respx.get("https://api.hunter.io/v2/email-finder").mock(
        return_value=httpx.Response(
            200,
            json={"data": {"email": "scott@cognition.ai", "score": 96}},
        )
    )
    res = query_hunter_api(
        domain="cognition.ai",
        first_name="Scott",
        last_name="Wu",
        api_key="fake-hunter-key",
    )
    assert res is not None
    assert res["email"] == "scott@cognition.ai"
    assert res["confidence"] == 96


def test_discover_founding_team_emails_end_to_end() -> None:
    with patch(
        "fundwatch.email_finder.verify_mx",
        return_value=(True, "Google Workspace", ["smtp.google.com"]),
    ):
        with patch(
            "fundwatch.email_finder.scrape_domain_emails", return_value=["contact@cognition.ai"]
        ):
            with patch("fundwatch.email_finder.verify_smtp_probe", return_value=None):
                domain, founders, emails = discover_founding_team_emails(
                    company_name="Cognition",
                    article_text="AI startup Cognition raises $175M. Founded by Scott Wu.",
                    known_domain="cognition.ai",
                    known_founders=[{"name": "Scott Wu", "role": "CEO"}],
                )

                assert domain == "cognition.ai"
                assert len(founders) >= 1
                assert any(f["name"] == "Scott Wu" for f in founders)

                email_addresses = [e["email"] for e in emails]
                assert "scott@cognition.ai" in email_addresses
                assert "founders@cognition.ai" in email_addresses
                assert "contact@cognition.ai" in email_addresses

                # Verify sorting by confidence
                assert emails[0]["confidence"] >= emails[-1]["confidence"]


def test_format_article_message_with_founder_emails() -> None:
    art = Article(
        id="test-1",
        feed_name="TechCrunch",
        title="Cognition raises $175M",
        link="https://techcrunch.com/1",
        published_at="2026-11-20T12:00:00Z",
    )
    ext = Extraction(
        article_id="test-1",
        company="Cognition",
        domain="cognition.ai",
        founders=[{"name": "Scott Wu", "role": "CEO"}],
        emails=[
            {
                "name": "Scott Wu",
                "role": "CEO",
                "email": "scott@cognition.ai",
                "confidence": 98,
                "verified": True,
            },
            {
                "name": "Founding Team",
                "role": "Founder Inbox",
                "email": "founders@cognition.ai",
                "confidence": 88,
                "verified": True,
            },
        ],
    )

    msg = format_article_message(art, ext)
    assert "🌐 Website: cognition.ai" in msg
    assert "✉️ Founding Team & Contacts:" in msg
    assert "Scott Wu (CEO): scott@cognition.ai [Verified]" in msg
    assert "founders@cognition.ai [Verified]" in msg


def test_extract_company_name_robustness() -> None:
    assert (
        extract_company_name("Exclusive: Celcius Logistics Eyes ₹100 Cr To Expand")
        == "Celcius Logistics"
    )
    assert (
        extract_company_name("Dialysis care provider VitusCare raises $3 Mn in Series B round")
        == "VitusCare"
    )
    assert (
        extract_company_name("Decoding captable of Aman Gupta and Ranveer Singh’s H.I.M")
        == "H.I.M"
    )
    assert (
        extract_company_name("Centre’s Antariksh VC Fund Leads SatSure’s ₹200 Cr Series B Round")
        == "SatSure"
    )
    assert (
        extract_company_name("Former Alibaba exec’s Everful raises $48.5M to connect retailers")
        == "Everful"
    )
    assert (
        extract_company_name("Disseqt AI raises $8 Mn led by Gresham House Ventures")
        == "Disseqt AI"
    )
    assert (
        extract_company_name("Sarvam’s Token Factory Raises India’s AI Inference Stakes")
        == "Sarvam"
    )


def test_extract_founders_from_text_multi_founder() -> None:
    text_vitus = (
        "Founded in 2017 by Prabhat Shrivastava, VitusCare operates through a capital-light model."
    )
    founders_vitus = extract_founders_from_text(text_vitus)
    assert len(founders_vitus) == 1
    assert founders_vitus[0]["name"] == "Prabhat Shrivastava"

    text_disseqt = (
        "Founded in late 2025 by Apoorva Kumar, Manish Atri and Cyril Treacy, "
        "Disseqt AI provides an AI governance platform."
    )
    founders_disseqt = extract_founders_from_text(text_disseqt)
    names_disseqt = [f["name"] for f in founders_disseqt]
    assert "Apoorva Kumar" in names_disseqt
    assert "Manish Atri" in names_disseqt
    assert "Cyril Treacy" in names_disseqt


def test_is_port_25_accessible_cached() -> None:
    with patch("socket.socket") as mock_sock:
        mock_instance = MagicMock()
        mock_instance.connect.side_effect = Exception("Connection timed out")
        mock_sock.return_value.__enter__.return_value = mock_instance

        # Reset cache
        import fundwatch.email_finder as ef

        ef._CAN_CONNECT_PORT_25 = None

        accessible = is_port_25_accessible("smtp.google.com")
        assert accessible is False

        # When blocked, verify_smtp_probe returns None immediately
        probe_res = verify_smtp_probe("test@google.com", "smtp.google.com")
        assert probe_res is None

