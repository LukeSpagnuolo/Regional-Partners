import os
from dash_auth_external import DashAuthExternal
from settings import AUTH_URL, TOKEN_URL, APP_URL, CLIENT_ID, CLIENT_SECRET

import logging
logger = logging.getLogger(__name__)
import os

auth = DashAuthExternal(
    AUTH_URL,
    TOKEN_URL,
    app_url=APP_URL,
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
)
server = auth.server  # expose the Flask server for app.py
# Ensure Flask has a stable secret key so session cookies work across requests.
# Prefer setting `SECRET_KEY` or `FLASK_SECRET` in the environment (Posit app settings).
secret = os.environ.get("SECRET_KEY") or os.environ.get("FLASK_SECRET")
if secret:
    server.secret_key = secret
else:
    # generate a temporary key (not suitable for production across restarts)
    server.secret_key = os.urandom(24)
    logger.warning("No SECRET_KEY/FLASK_SECRET env var set; using a temporary secret. Set one in Posit to persist sessions.")

# Recommended cookie settings for deployments behind HTTPS/proxies
server.config.setdefault("SESSION_COOKIE_SAMESITE", "None")
server.config.setdefault("SESSION_COOKIE_SECURE", True)