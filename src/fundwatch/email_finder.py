"""Founding team and executive email discovery engine.

Combines domain resolution, founder extraction, pattern permutation,
MX record verification, website contact scraping, and optional Hunter.io enrichment.
"""

from __future__ import annotations

import logging
import re
import smtplib
from typing import Any
from urllib.parse import urlparse

import dns.resolver
import httpx

logger = logging.getLogger(__name__)

# Outlets, aggregators, and public domains to ignore when resolving company website
IGNORED_DOMAINS = {
    "techcrunch.com",
    "inc42.com",
    "entrackr.com",
    "yourstory.com",
    "crunchbase.com",
    "bloomberg.com",
    "reuters.com",
    "twitter.com",
    "x.com",
    "linkedin.com",
    "facebook.com",
    "youtube.com",
    "instagram.com",
    "github.com",
    "medium.com",
    "substack.com",
    "google.com",
    "apple.com",
    "wikipedia.org",
    "example.com",
}

# Stopwords that are not actual human founder names
FOUNDER_STOPWORDS = {
    "former",
    "weekly",
    "report",
    "startup",
    "company",
    "funding",
    "round",
    "fund",
    "alibaba",
    "google",
    "microsoft",
    "amazon",
    "meta",
    "the",
    "and",
    "new",
    "top",
    "market",
    "chief",
    "officer",
}

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")


def clean_domain(raw_url_or_domain: str | None) -> str | None:
    """Normalize raw URL or domain string to a clean domain hostname (e.g. 'cognition.ai')."""
    if not raw_url_or_domain:
        return None
    candidate = raw_url_or_domain.strip().lower()
    if candidate.startswith(("http://", "https://")):
        parsed = urlparse(candidate)
        candidate = parsed.netloc
    candidate = candidate.split("/")[0].split(":")[0]
    if candidate.startswith("www."):
        candidate = candidate[4:]
    if not candidate or "." not in candidate:
        return None
    if candidate in IGNORED_DOMAINS:
        return None
    return candidate


def verify_mx(domain: str) -> tuple[bool, str | None, list[str]]:
    """Check whether a domain has valid MX records and identify the mail provider."""
    try:
        answers = dns.resolver.resolve(domain, "MX", lifetime=3.0)
        mx_hosts = [str(r.exchange).rstrip(".").lower() for r in answers]
        if not mx_hosts:
            return False, None, []

        provider = "Standard MX"
        combined = " ".join(mx_hosts)
        if "google.com" in combined or "googlemail.com" in combined or "aspmx" in combined:
            provider = "Google Workspace"
        elif "outlook.com" in combined or "microsoft.com" in combined:
            provider = "Microsoft 365"
        elif "zoho.com" in combined:
            provider = "Zoho Mail"
        elif "proton" in combined:
            provider = "Proton Mail"
        elif "secureserver" in combined:
            provider = "GoDaddy"

        return True, provider, mx_hosts
    except Exception:
        return False, None, []


def resolve_company_domain(
    company_name: str,
    article_text: str = "",
    client: httpx.Client | None = None,
) -> str | None:
    """
    Resolve startup's official domain:
    1. Search article links/text for non-news domains.
    2. Clearbit Autocomplete API lookup.
    3. Slug permutation with common TLDs verified via MX lookup.
    """
    if not company_name:
        return None

    # Step 1: Scan article text for external URLs
    urls_in_text = re.findall(r"https?://[^\s'\"<>]+", article_text)
    for u in urls_in_text:
        d = clean_domain(u)
        if d and d not in IGNORED_DOMAINS:
            has_mx, _, _ = verify_mx(d)
            if has_mx:
                return d

    # Step 2: Clearbit Autocomplete API
    try:
        url = f"https://autocomplete.clearbit.com/v1/companies/suggest?query={company_name}"
        if client:
            resp = client.get(url, timeout=3.0)
        else:
            with httpx.Client(timeout=3.0) as local_client:
                resp = local_client.get(url)

        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list) and data:
                first_domain = clean_domain(data[0].get("domain"))
                if first_domain:
                    has_mx, _, _ = verify_mx(first_domain)
                    if has_mx:
                        return first_domain
    except Exception as exc:
        logger.debug("Clearbit domain lookup failed for %s: %s", company_name, exc)

    # Step 3: Clean slug + Common TLD permutation checked against MX records
    clean_slug = re.sub(r"[^\w]", "", company_name.lower())
    if len(clean_slug) >= 3:
        for tld in [".com", ".ai", ".co", ".in", ".io", ".tech"]:
            candidate = f"{clean_slug}{tld}"
            has_mx, _, _ = verify_mx(candidate)
            if has_mx:
                return candidate

    return None


def extract_founders_from_text(text: str) -> list[dict[str, str]]:
    """Extract founder and co-founder names from headlines and summaries using regex heuristics."""
    founders: list[dict[str, str]] = []
    seen_names: set[str] = set()

    def add_founder(raw_name: str, role: str) -> None:
        name_clean = " ".join(raw_name.strip().split())
        # Filter invalid or short names
        words = name_clean.split()
        if len(words) < 2 or len(words) > 3:
            return
        if any(w.lower() in FOUNDER_STOPWORDS for w in words):
            return
        if not all(w[0].isupper() for w in words if w):
            return
        if name_clean.lower() not in seen_names:
            seen_names.add(name_clean.lower())
            founders.append({"name": name_clean, "role": role})

    # Pattern 1: "founded by X and Y"
    pattern1 = re.compile(
        r"(?:founded by|co-founded by)\s+"
        r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?(?:\s+(?:and|&)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)?)",
        re.IGNORECASE,
    )
    for m in pattern1.finditer(text):
        matched_str = m.group(1)
        sub_names = re.split(r"\s+(?:and|&)\s+", matched_str, flags=re.IGNORECASE)
        for sn in sub_names:
            add_founder(sn, "Founder")

    # Pattern 2: "X, co-founder and CEO" or "X, founder"
    pattern2 = re.compile(
        r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)[,\s]+(?:co-founder|founder|ceo)",
        re.IGNORECASE,
    )
    for m in pattern2.finditer(text):
        add_founder(m.group(1), "Co-Founder & CEO")

    # Pattern 3: "CEO and co-founder X"
    pattern3 = re.compile(
        r"(?:co-founder|founder|ceo)\s+(?:and\s+ceo\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
        re.IGNORECASE,
    )
    for m in pattern3.finditer(text):
        add_founder(m.group(1), "Co-Founder")

    return founders


def generate_founder_emails(founder_name: str, domain: str) -> list[str]:
    """Generate high-probability email patterns for a founder at a given domain."""
    clean_name = re.sub(r"[^a-zA-Z\s]", "", founder_name).strip().lower()
    parts = clean_name.split()
    if not parts:
        return []

    first = parts[0]
    last = parts[-1] if len(parts) > 1 else ""

    candidates: list[str] = []
    # 1. first@domain (over 70% of founders use first name)
    candidates.append(f"{first}@{domain}")

    if last:
        # 2. first.last@domain
        candidates.append(f"{first}.{last}@{domain}")
        # 3. firstlast@domain
        candidates.append(f"{first}{last}@{domain}")
        # 4. f_last@domain
        candidates.append(f"{first[0]}{last}@{domain}")
        # 5. first_last@domain
        candidates.append(f"{first}_{last}@{domain}")

    return candidates


def scrape_domain_emails(domain: str, client: httpx.Client | None = None) -> list[str]:
    """Scrape public contact emails matching the domain from website home/contact pages."""
    discovered: set[str] = set()
    headers = {"User-Agent": "fundwatch/0.1 (founder contact discovery)"}
    endpoints = [f"https://{domain}", f"https://{domain}/contact", f"https://{domain}/about"]

    def process_url(u: str) -> None:
        try:
            if client:
                r = client.get(u, headers=headers, timeout=3.0, follow_redirects=True)
            else:
                with httpx.Client(timeout=3.0, follow_redirects=True) as local_c:
                    r = local_c.get(u, headers=headers)
            if r.status_code == 200:
                matches = EMAIL_RE.findall(r.text)
                for email in matches:
                    clean_e = email.lower().rstrip(".,;:!?)'\"")
                    if clean_e.endswith(f"@{domain}"):
                        discovered.add(clean_e)
        except Exception:
            pass

    for ep in endpoints:
        process_url(ep)
        if discovered:
            break

    return list(discovered)


def verify_smtp_probe(email: str, mx_host: str, timeout: float = 3.0) -> bool | None:
    """
    Attempt an SMTP RCPT TO handshake to probe deliverability.
    Returns True if accepted (250), False if rejected (550), None if connection/port 25 blocked.
    """
    try:
        with smtplib.SMTP(mx_host, 25, timeout=timeout) as smtp:
            smtp.helo("fundwatch.local")
            smtp.mail("verify@fundwatch.local")
            code, _ = smtp.rcpt(email)
            if code == 250:
                return True
            if code >= 500:
                return False
    except Exception:
        pass
    return None


def query_hunter_api(
    domain: str,
    first_name: str,
    last_name: str,
    api_key: str,
    client: httpx.Client | None = None,
) -> dict[str, Any] | None:
    """Enrich with Hunter.io email finder API if API key is configured."""
    if not api_key:
        return None
    try:
        url = "https://api.hunter.io/v2/email-finder"
        params = {
            "domain": domain,
            "first_name": first_name,
            "last_name": last_name,
            "api_key": api_key,
        }
        if client:
            resp = client.get(url, params=params, timeout=4.0)
        else:
            with httpx.Client(timeout=4.0) as local_client:
                resp = local_client.get(url, params=params)
        if resp.status_code == 200:
            data = resp.json().get("data", {})
            found_email = data.get("email")
            if found_email:
                return {
                    "email": found_email.lower(),
                    "confidence": data.get("score", 90),
                    "source": "hunter_api",
                }
    except Exception as exc:
        logger.debug("Hunter.io lookup error for %s @ %s: %s", first_name, domain, exc)
    return None


def discover_founding_team_emails(
    company_name: str,
    article_text: str = "",
    known_domain: str | None = None,
    known_founders: list[dict[str, str]] | None = None,
    hunter_api_key: str | None = None,
    http_client: httpx.Client | None = None,
) -> tuple[str | None, list[dict[str, str]], list[dict[str, Any]]]:
    """
    Master orchestrator to discover company domain, founders, and verified founder emails.
    Returns: (domain, founders, emails)
    """
    # 1. Resolve company domain
    domain = clean_domain(known_domain)
    if not domain:
        domain = resolve_company_domain(company_name, article_text, client=http_client)

    # 2. Extract or use known founders
    founders: list[dict[str, str]] = []
    if known_founders:
        founders.extend(known_founders)
    if not founders:
        founders = extract_founders_from_text(article_text)

    emails: list[dict[str, Any]] = []
    seen_emails: set[str] = set()

    if not domain:
        return domain, founders, emails

    # 3. Validate MX records
    has_mx, provider, mx_hosts = verify_mx(domain)
    primary_mx = mx_hosts[0] if mx_hosts else None

    # 4. Scrape website for direct contact emails
    scraped = scrape_domain_emails(domain, client=http_client)
    for s_email in scraped:
        if s_email not in seen_emails:
            seen_emails.add(s_email)
            emails.append(
                {
                    "name": "Company Contact",
                    "role": "General Contact",
                    "email": s_email,
                    "confidence": 95,
                    "verified": True,
                    "source": "website_scrape",
                    "provider": provider,
                }
            )

    # 5. Generate and probe founder personal email addresses
    for founder in founders:
        f_name = founder.get("name", "")
        f_role = founder.get("role", "Founder")
        parts = f_name.split()
        first_name = parts[0] if parts else ""
        last_name = parts[-1] if len(parts) > 1 else ""

        # Check Hunter.io first if API key configured
        hunter_match = None
        if hunter_api_key and first_name:
            hunter_match = query_hunter_api(
                domain, first_name, last_name, hunter_api_key, client=http_client
            )
            if hunter_match and hunter_match["email"] not in seen_emails:
                seen_emails.add(hunter_match["email"])
                emails.append(
                    {
                        "name": f_name,
                        "role": f_role,
                        "email": hunter_match["email"],
                        "confidence": hunter_match["confidence"],
                        "verified": True,
                        "source": "hunter_api",
                        "provider": provider,
                    }
                )

        # Generate standard founder patterns
        candidates = generate_founder_emails(f_name, domain)
        for idx, cand_email in enumerate(candidates):
            if cand_email in seen_emails:
                continue

            # First pattern (first@domain) gets highest confidence
            base_confidence = 92 if idx == 0 else (85 if idx == 1 else 70)
            is_deliverable = None
            if primary_mx:
                is_deliverable = verify_smtp_probe(cand_email, primary_mx)

            if is_deliverable is False:
                # Mailbox does not exist according to server
                continue

            verified_flag = bool(has_mx and (is_deliverable is True or idx == 0))
            seen_emails.add(cand_email)
            emails.append(
                {
                    "name": f_name,
                    "role": f_role,
                    "email": cand_email,
                    "confidence": 98 if is_deliverable is True else base_confidence,
                    "verified": verified_flag,
                    "source": "smtp_probe" if is_deliverable is True else "pattern_mx",
                    "provider": provider,
                }
            )

    # 6. Always include generic founder inboxes if MX is verified
    if has_mx:
        for generic_user in ["founders", "founder", "ceo"]:
            gen_email = f"{generic_user}@{domain}"
            if gen_email not in seen_emails:
                seen_emails.add(gen_email)
                emails.append(
                    {
                        "name": "Founding Team",
                        "role": "Founder Inbox",
                        "email": gen_email,
                        "confidence": 88,
                        "verified": True,
                        "source": "role_inbox",
                        "provider": provider,
                    }
                )

    # Sort emails by confidence descending
    emails.sort(key=lambda x: int(x.get("confidence", 0)), reverse=True)
    return domain, founders, emails
