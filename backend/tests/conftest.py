"""Keep the test suite offline.

app.main loads backend/.env at import time, and python-dotenv never overrides
variables that already exist. Pinning every setting here, before any test
module imports the app, means a developer's live keys, replay path or study
database can never reach a test. Individual tests still opt in with monkeypatch.
"""

import os
import tempfile
from pathlib import Path

OFFLINE = {
    "BEANY_LLM_MODE": "mock",
    "BEANY_SEARCH_PROVIDER": "catalogue",
    "BEANY_RESEARCH_KEY": "",
    "BEANY_DB": str(Path(tempfile.mkdtemp(prefix="beany-tests-")) / "beany.sqlite3"),
    "OPENAI_API_KEY": "",
    "OPENAI_BASE_URL": "",
    "OPENAI_MODEL": "",
    "OPENAI_API_MODE": "responses",
    "OPENAI_STRUCTURED_MODE": "schema",
    "OPENAI_REASONING_EFFORT": "",
    "BROWSER_USE_API_KEY": "",
    "BROWSER_USE_ALLOWED_DOMAINS": "",
    "BROWSER_USE_REPLAY": "",
    "BROWSER_USE_MODEL": "",
    "BROWSER_USE_TIMEOUT_SECONDS": "120",
    "BROWSER_USE_MAX_COST_USD": "0.5",
    "FRONTEND_ORIGIN": "http://localhost:3000",
}
os.environ.update(OFFLINE)
