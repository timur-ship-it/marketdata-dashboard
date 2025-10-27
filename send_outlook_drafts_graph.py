#!/usr/bin/env python3
import msal, requests, json, webbrowser, threading
from urllib.parse import urlencode
from http.server import HTTPServer, BaseHTTPRequestHandler

# === Replace with your Azure app info ===
CLIENT_ID = "YOUR_CLIENT_ID"
CLIENT_SECRET = "YOUR_CLIENT_SECRET"
TENANT_ID = "YOUR_TENANT_ID"
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPES = ["Mail.ReadWrite", "Mail.Send"]

# === OAuth helper ===
class OAuthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = self.path.split("?", 1)[-1]
        params = dict(q.split("=") for q in query.split("&") if "=" in q)
        self.server.auth_code = params.get("code")
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Authentication successful. You can close this tab.")
    def log_message(self, *args): pass

def get_token():
    app = msal.ConfidentialClientApplication(
        CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET
    )
    flow = app.initiate_auth_code_flow(SCOPES, redirect_uri="http://localhost:8000")
    server = HTTPServer(("localhost", 8000), OAuthHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    webbrowser.open(flow["auth_uri"])
    print("Please sign in via browser...")
    while not hasattr(server, "auth_code"):
        pass
    server.shutdown()
    result = app.acquire_token_by_auth_code_flow(flow, {"code": server.auth_code})
    if "access_token" in result:
        return result["access_token"]
    raise Exception(result.get("error_description", "Authentication failed"))

token = get_token()
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
GRAPH_URL = "https://graph.microsoft.com/v1.0/me"

# === Step 1: List existing drafts ===
resp = requests.get(f"{GRAPH_URL}/mailFolders('Drafts')/messages", headers=headers)
if resp.status_code != 200:
    raise Exception(f"Failed to list drafts: {resp.status_code} {resp.text}")

drafts = resp.json().get("value", [])
print(f"\\nFound {len(drafts)} drafts.\\n")

# === Step 2: Choose which ones to send ===
to_send = []
for d in drafts:
    subj = d.get("subject", "")
    msgid = d.get("id", "")
    recipients = [r["emailAddress"]["address"] for r in d.get("toRecipients", [])]
    print(f"→ {subj} | To: {', '.join(recipients)} | ID: {msgid}")
    if "Inquiry — Bond/Sukūk Data API Coverage" in subj:
        to_send.append(msgid)

print(f"\\nPreparing to send {len(to_send)} draft(s)...")

# === Step 3: Send drafts ===
for msgid in to_send:
    send_resp = requests.post(f"{GRAPH_URL}/messages/{msgid}/send", headers=headers)
    if send_resp.status_code == 202:
        print(f"✅ Sent draft {msgid}")
    else:
        print(f"❌ Failed to send {msgid}: {send_resp.status_code} {send_resp.text}")

print("\\nDone.")
