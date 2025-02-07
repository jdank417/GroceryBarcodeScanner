from flask import Flask, render_template, request, flash, session, redirect, url_for, Response, jsonify
import pandas as pd
import os
import logging
from functools import lru_cache
import time
import sqlite3
import datetime
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Use environment variables in production.

ADMIN_PASSWORD = "admin"  # Also use environment variables in production.

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Path to your Excel file
EXCEL_FILE_PATH = 'Item Database/output.xlsx'
df = pd.read_excel(EXCEL_FILE_PATH, dtype={'ItemNumber': str})
df["ItemNumber"] = df["ItemNumber"].str.replace(r'\.0$', '', regex=True).str.strip()

# Prometheus counters
lookup_success_counter = Counter("lookup_success_total", "Total successful UPC lookups")
lookup_failure_counter = Counter("lookup_failure_total", "Total UPC lookups that did not find an item")
barcode_scan_failure_counter = Counter("barcode_scan_failure_total", "Total barcode decode failures reported by client")

DATABASE = "metrics.db"

def init_db():
    """
    Initialize the SQLite database.
    WARNING: This drops the existing 'events' table if it exists.
    Remove or modify the DROP TABLE line if you want to keep old data.
    """
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    # Drop old table -- comment out if you need to keep existing data
    c.execute("DROP TABLE IF EXISTS events")

    # Create new table including sku and item_name columns
    c.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT,
            timestamp INTEGER,
            sku TEXT,
            item_name TEXT
        )
    """)
    conn.commit()
    conn.close()

def log_event_sql(event_type, sku=None, item_name=None):
    """
    Log an event to the SQLite DB, including optional SKU and item name.
    """
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("""
        INSERT INTO events (event_type, timestamp, sku, item_name)
        VALUES (?, ?, ?, ?)
    """, (event_type, int(time.time()), sku, item_name))
    conn.commit()
    conn.close()

def get_aggregated_counts():
    """
    Return total counts for each event type.
    """
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    counts = {}
    for event in ["lookup_success", "lookup_failure", "barcode_scan_failure"]:
        c.execute("SELECT COUNT(*) FROM events WHERE event_type = ?", (event,))
        counts[event] = c.fetchone()[0]
    conn.close()
    return counts

init_db()

@lru_cache(maxsize=100)
def lookup_item(barcode_data):
    """
    Look up the item in the Excel DataFrame by SKU.
    If found, increment success counters and log the success with SKU + item_name.
    Otherwise, log a failure with the SKU.
    """
    barcode_data = str(barcode_data).strip()
    item_info = df[df["ItemNumber"] == barcode_data]
    if not item_info.empty:
        item_name = item_info["ItemName"].values[0]
        item_price = item_info["ItemPrice"].values[0]

        # Prometheus + DB
        lookup_success_counter.inc()
        log_event_sql("lookup_success", sku=barcode_data, item_name=item_name)
        return item_name, item_price
    else:
        lookup_failure_counter.inc()
        log_event_sql("lookup_failure", sku=barcode_data, item_name=None)
        return None, None

@app.route("/", methods=["GET", "POST"])
def index():
    """
    Main page for manual barcode lookups.
    """
    if request.method == "POST":
        barcode_id = request.form.get("barcode_id")
        if barcode_id:
            item_name, item_price = lookup_item(barcode_id)
            if item_name and item_price:
                flash(f"Item: {item_name}, Price: ${item_price}", "info")
            else:
                flash("Item not found in the Excel file.", "warning")
        else:
            flash("Please enter a valid SKU (barcode).", "error")
    return render_template("index.html")

@app.route("/log_client_error", methods=["POST"])
def log_client_error():
    """
    If the client can provide SKU in the error, we could log that here as well.
    For now, we just log the error details. Adjust if you want to store SKU or item_name.
    """
    data = request.get_json()
    error = data.get("error", "No error provided")
    details = data.get("details", "")
    # Optionally capture sku if client provides it
    sku = data.get("sku", None)

    barcode_scan_failure_counter.inc()
    log_event_sql("barcode_scan_failure", sku=sku, item_name=details)

    logger.error(f"Client error: {error} – {details}")
    return jsonify({"status": "logged"}), 200

@app.route("/metrics")
def metrics():
    """
    Expose Prometheus-format metrics at /metrics.
    """
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

@app.route("/api/historical")
def historical_data():
    """
    Returns aggregated counts for a given event type, grouped by hour,
    within an optional start/end date range (default last 7 days).
    """
    event_type = request.args.get("event_type")
    if not event_type:
        return jsonify({"error": "event_type parameter required"}), 400

    start_date_str = request.args.get("start_date")
    end_date_str = request.args.get("end_date")

    if not start_date_str or not end_date_str:
        today = datetime.date.today()
        default_start = today - datetime.timedelta(days=7)
        start_date_str = start_date_str or default_start.isoformat()
        end_date_str = end_date_str or today.isoformat()

    try:
        start_dt = datetime.datetime.strptime(start_date_str, "%Y-%m-%d")
        end_dt = datetime.datetime.strptime(end_date_str, "%Y-%m-%d")
        # End of that day
        end_dt = end_dt + datetime.timedelta(days=1) - datetime.timedelta(seconds=1)
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

    start_ts = int(start_dt.timestamp())
    end_ts = int(end_dt.timestamp())

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    # Fixed hour grouping
    group_expression = "strftime('%Y-%m-%d %H:00:00', datetime(timestamp, 'unixepoch', 'localtime'))"

    query = f"""
        SELECT {group_expression} as time_group, COUNT(*)
        FROM events
        WHERE event_type = ?
          AND timestamp >= ?
          AND timestamp <= ?
        GROUP BY time_group
        ORDER BY time_group ASC
    """
    c.execute(query, (event_type, start_ts, end_ts))
    rows = c.fetchall()
    conn.close()

    result = []
    for row in rows:
        time_str = row[0]
        count = row[1]
        result.append({"hour": time_str, "count": count})

    return jsonify(result)

@app.route("/api/item_events")
def item_events():
    """
    Return a list of success/failure events (lookup_success, lookup_failure),
    with their time, sku, and item_name, for a given date range.
    Default: last 7 days.
    """
    start_date_str = request.args.get("start_date")
    end_date_str = request.args.get("end_date")

    if not start_date_str or not end_date_str:
        today = datetime.date.today()
        default_start = today - datetime.timedelta(days=7)
        start_date_str = start_date_str or default_start.isoformat()
        end_date_str = end_date_str or today.isoformat()

    try:
        start_dt = datetime.datetime.strptime(start_date_str, "%Y-%m-%d")
        end_dt = datetime.datetime.strptime(end_date_str, "%Y-%m-%d")
        end_dt = end_dt + datetime.timedelta(days=1) - datetime.timedelta(seconds=1)
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

    start_ts = int(start_dt.timestamp())
    end_ts = int(end_dt.timestamp())

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("""
        SELECT event_type, timestamp, sku, item_name
        FROM events
        WHERE event_type IN ('lookup_success', 'lookup_failure')
          AND timestamp >= ?
          AND timestamp <= ?
        ORDER BY timestamp DESC
    """, (start_ts, end_ts))
    rows = c.fetchall()
    conn.close()

    events = []
    for (etype, ts, sku, iname) in rows:
        dt_str = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
        events.append({
            "event_type": etype,
            "time": dt_str,
            "sku": sku,
            "item_name": iname
        })

    return jsonify(events)

@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    """
    Admin-protected dashboard. Shows aggregated metrics and
    a chart of hourly data for each event type + item-level events.
    """
    if "admin" not in session:
        if request.method == "POST":
            password = request.form.get("password")
            if password == ADMIN_PASSWORD:
                session["admin"] = True
                return redirect(url_for("dashboard"))
            else:
                flash("Incorrect password. Please try again.", "error")
        return render_template("admin_login.html")

    # Admin is authenticated, gather total metrics
    counts = get_aggregated_counts()
    success = counts.get("lookup_success", 0)
    fail = counts.get("lookup_failure", 0)
    total = success + fail
    success_rate = (success / total) * 100 if total else 0

    metrics_data = {
        "lookup_success_total": success,
        "lookup_failure_total": fail,
        "barcode_scan_failure_total": counts.get("barcode_scan_failure", 0),
        "success_rate": round(success_rate, 2)
    }
    return render_template("dashboard.html", metrics=metrics_data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
