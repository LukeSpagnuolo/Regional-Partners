import os
from dotenv import load_dotenv
load_dotenv()

"""
.env example

CLIENT_ID=<from oauth>
CLIENT_SECRET=<from oauth>

SITE_URL=http://<address>:8000
APP_URL=http://<address>:8050

"""

SITE_URL = os.environ.get("SITE_URL","http://127.0.0.1:8000")
APP_URL = os.environ.get("APP_URL","http://127.0.0.1:8050")

AUTH_URL = f"{SITE_URL}/o/authorize"
TOKEN_URL = f"{SITE_URL}/o/token/"
CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")

SPORT_ORG_ENDPOINT = f"/api/registration/organization/"
PROFILE_ENDPOINT = f"/api/registration/profile/"

REPORT_COLUMNS_ENDPOINT = "/api/registration/report-columns/"
REPORT_ROWS_ENDPOINT = "/api/registration/report-rows/"
