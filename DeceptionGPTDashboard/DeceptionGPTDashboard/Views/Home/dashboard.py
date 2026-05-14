from flask import Flask, render_template_string
import json
import os

app = Flask(__name__)

LOG_FILE = "honeypot_logs.jsonl"

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Honeypot Dashboard</title>
    <style>
        body { font-family: Arial; background: #111; color: #0f0; }
        table { width: 100%; border-collapse: collapse; }
        th, td { border: 1px solid #0f0; padding: 8px; }
        th { background: #222; }
    </style>
</head>
<body>

<h1> Honeypot Dashboard</h1>

<table>
<tr>
<th>Time</th>
<th>Event</th>
<th>IP</th>
<th>Username</th>
<th>Password</th>
</tr>

{% for log in logs %}
<tr>
<td>{{ log.timestamp }}</td>
<td>{{ log.event_type }}</td>
<td>{{ log.source_ip }}</td>
<td>{{ log.username or '' }}</td>
<td>{{ log.password or '' }}</td>
</tr>
{% endfor %}

</table>

</body>
</html>
"""

@app.route("/")
def index():
    logs = []

    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            for line in f:
                logs.append(json.loads(line))

    return render_template_string(HTML, logs=logs[::-1])

if __name__ == "__main__":
    app.run(debug=True)