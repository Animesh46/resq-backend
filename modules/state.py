"""Global in-memory state for ResQ."""

# Ingested and classified news articles
raw_articles = []

# Active alerts built from raw_articles (used by alerts/risk routers)
active_alerts = []

# Historical / experimental fields kept for compatibility
processed_alerts = []
verified_alerts = []
risk_cache = {}
last_ingestion_time = None

# Pending SOS events (for retry / audit)
pending_distress = []

# Safety check loops keyed by user_id
safety_loops = {}