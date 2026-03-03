"""
News Ingestion Module — REBUILT
Uses GNews API (free, no RSS parsing issues) + Gemini web search as fallback.
GNews gives clean, current, searchable Indian disaster news.

Get free GNews API key at: https://gnews.io (free tier: 100 req/day)
"""

import asyncio
import logging
import hashlib
from datetime import datetime
from typing import List, Optional
import httpx

from config import INGESTION_INTERVAL, GNEWS_API_KEY
from models import NewsItem
from modules.gemini import classify_disaster, search_current_disasters
from modules import state

logger = logging.getLogger(__name__)

# GNews search queries — targeted for Indian disasters
GNEWS_QUERIES = [
    "flood India",
    "cyclone India",
    "earthquake India",
    "heatwave India",
    "heavy rain India disaster",
    "NDMA NDRF emergency India",
    "IMD alert warning India",
    "landslide India",
]

GNEWS_BASE = "https://gnews.io/api/v4/search"


def _item_id(title: str, url: str) -> str:
    return hashlib.md5(f"{url}{title}".encode()).hexdigest()[:12]


async def fetch_gnews(query: str) -> List[NewsItem]:
    """Fetch news from GNews API."""
    if not GNEWS_API_KEY:
        return []

    items = []
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            params = {
                "q": query,
                "lang": "en",
                "country": "in",
                "max": 10,
                "apikey": GNEWS_API_KEY,
                "sortby": "publishedAt",
            }
            resp = await client.get(GNEWS_BASE, params=params)
            if resp.status_code != 200:
                logger.warning(f"GNews query '{query}': HTTP {resp.status_code}")
                return []

            data = resp.json()
            articles = data.get("articles", [])
            logger.info(f"  GNews '{query}': {len(articles)} articles")

            for art in articles:
                title = art.get("title", "").strip()
                description = art.get("description", "") or ""
                content = art.get("content", "") or ""
                summary = (description or content)[:600]
                url = art.get("url", "")
                source_name = art.get("source", {}).get("name", "Unknown")
                published = art.get("publishedAt", str(datetime.utcnow()))

                if not title or not url:
                    continue

                # Determine source type
                official_sources = ["ndma", "imd", "ndrf", "government", "pib", "mha"]
                source_type = "national"
                if any(s in source_name.lower() for s in official_sources):
                    source_type = "official"

                items.append(NewsItem(
                    title=title,
                    summary=summary,
                    source=source_name,
                    url=url,
                    published=published,
                    source_type=source_type,
                ))
    except Exception as e:
        logger.warning(f"  GNews fetch failed for '{query}': {e}")
    return items


async def fetch_rss_fallback() -> List[NewsItem]:
    """
    RSS fallback when GNews key not available.
    Uses feeds known to have good disaster coverage.
    """
    import feedparser

    FEEDS = [
        ("https://timesofindia.indiatimes.com/rssfeedstopstories.cms", "national"),
        ("https://www.thehindu.com/news/national/feeder/default.rss", "national"),
        ("https://feeds.feedburner.com/ndtvnews-top-stories", "national"),
        ("https://www.thehindu.com/news/cities/chennai/feeder/default.rss", "local"),
        ("https://www.thehindu.com/news/national/other-states/feeder/default.rss", "local"),
        ("https://www.thehindu.com/news/national/kerala/feeder/default.rss", "local"),
        ("https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml", "national"),
    ]

    KEYWORDS = [
        "flood", "flooding", "flooded", "inundation", "waterlog", "deluge", "submerged",
        "cyclone", "hurricane", "typhoon", "storm", "landfall", "low pressure",
        "earthquake", "tremor", "quake", "seismic",
        "wildfire", "forest fire",
        "heatwave", "heat wave", "scorching",
        "landslide", "mudslide",
        "cold wave", "frost", "dense fog",
        "heavy rain", "rainfall", "downpour", "monsoon", "cloudburst",
        "disaster", "emergency", "evacuation", "rescue",
        "IMD", "NDMA", "NDRF",
        "red alert", "orange alert", "yellow alert",
        "relief camp", "calamity", "devastation",
    ]

    items = []
    async with httpx.AsyncClient(
        timeout=15,
        headers={"User-Agent": "Mozilla/5.0 ResQ-DisasterBot/1.0"},
        follow_redirects=True,
    ) as client:
        for url, source_type in FEEDS:
            try:
                resp = await client.get(url)
                if resp.status_code != 200:
                    continue
                feed = feedparser.parse(resp.text)
                matched = 0
                for entry in feed.entries[:30]:
                    title = getattr(entry, "title", "").strip()
                    summary = (
                        getattr(entry, "summary", "")
                        or getattr(entry, "description", "")
                        or ""
                    ).strip()
                    link = getattr(entry, "link", url)
                    published = getattr(entry, "published", str(datetime.utcnow()))

                    text = (title + " " + summary).lower()
                    if not any(kw.lower() in text for kw in KEYWORDS):
                        continue

                    matched += 1
                    items.append(NewsItem(
                        title=title,
                        summary=summary[:600],
                        source=feed.feed.get("title", url),
                        url=link,
                        published=published,
                        source_type=source_type,
                    ))
                logger.info(f"  RSS {url[:55]}: {matched} matched")
            except Exception as e:
                logger.warning(f"  RSS failed {url[:50]}: {e}")

    return items


async def ingest_all() -> List[NewsItem]:
    """Fetch from GNews (preferred) or fall back to RSS."""
    items = []

    if GNEWS_API_KEY:
        logger.info("Using GNews API...")
        tasks = [fetch_gnews(q) for q in GNEWS_QUERIES]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, list):
                items.extend(r)
    else:
        logger.info("No GNEWS_API_KEY — using RSS fallback...")
        try:
            items = await fetch_rss_fallback()
        except ImportError:
            logger.warning("feedparser not installed. Install it: pip install feedparser")
            # Last resort: use Gemini to find current disasters
            items = await fetch_via_gemini_search()

    # Deduplicate by title
    seen = set()
    unique = []
    for item in items:
        key = item.title[:80].lower().strip()
        if key not in seen:
            seen.add(key)
            unique.append(item)

    logger.info(f"Total unique articles: {len(unique)}")
    return unique


async def fetch_via_gemini_search() -> List[NewsItem]:
    """
    Last resort: ask Gemini to provide current disaster news.
    Uses Gemini's knowledge of recent events.
    """
    logger.info("Using Gemini for current disaster news...")
    try:
        articles = await search_current_disasters()
        return articles
    except Exception as e:
        logger.error(f"Gemini search failed: {e}")
        return []


async def process_items(items: List[NewsItem]):
    """Classify each new article via Gemini and store in state."""
    seen_ids = {a["id"] for a in state.raw_articles}
    new_count = 0

    for item in items:
        item_id = _item_id(item.title, item.url)
        if item_id in seen_ids:
            continue

        try:
            logger.info(f"  Classifying: {item.title[:70]}")
            classification = await classify_disaster(item.title, item.summary)

            # Try to derive a more specific, human-readable location if the
            # classifier could not infer one. This helps geo filtering near user.
            loc = classification.location
            text_lower = (item.title + " " + item.summary + " " + item.source).lower()
            if loc == "Unknown":
                if "chennai" in text_lower or "adyar" in text_lower or "velachery" in text_lower:
                    loc = "Chennai, Tamil Nadu"
                elif "mumbai" in text_lower:
                    loc = "Mumbai, Maharashtra"
                elif "delhi" in text_lower or "new delhi" in text_lower:
                    loc = "New Delhi, Delhi"
                elif "kolkata" in text_lower:
                    loc = "Kolkata, West Bengal"
                elif "assam" in text_lower or "guwahati" in text_lower:
                    loc = "Assam, India"

            record = {
                "id": item_id,
                "title": item.title,
                "summary": item.summary,
                "source": item.source,
                "url": item.url,
                "published": item.published,
                "source_type": item.source_type,
                "disaster_type": classification.disaster_type,
                "location": loc,
                "severity": classification.severity,
                "escalation_score": classification.escalation_score,
                "credibility_score": classification.credibility_score,
                "summary_en": classification.summary_en,
                "ingested_at": datetime.utcnow().isoformat(),
            }
            state.raw_articles.append(record)
            seen_ids.add(item_id)
            new_count += 1
            logger.info(
                f"    -> {classification.disaster_type} | {classification.location} "
                f"| severity={classification.severity}"
            )
            await asyncio.sleep(0.5)  # avoid Gemini rate limits

        except Exception as e:
            logger.error(f"  Classification failed '{item.title[:50]}': {e}")

    logger.info(f"Added {new_count} new. Total in state: {len(state.raw_articles)}")
    state.raw_articles = state.raw_articles[-500:]


async def run_ingestion_loop():
    logging.basicConfig(level=logging.INFO)
    logger.info("=" * 60)
    logger.info("ResQ ingestion loop started")
    logger.info("=" * 60)

    while True:
        try:
            logger.info(f"\n[{datetime.utcnow().strftime('%H:%M:%S UTC')}] Ingestion cycle...")
            items = await ingest_all()
            await process_items(items)
        except Exception as e:
            logger.error(f"Ingestion loop error: {e}", exc_info=True)
        logger.info(f"Next cycle in {INGESTION_INTERVAL}s\n")
        await asyncio.sleep(INGESTION_INTERVAL)
