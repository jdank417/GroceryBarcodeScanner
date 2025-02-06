from flask import Flask, render_template, request, flash, session, redirect, url_for, Response, jsonify
import pandas as pd
import os
import logging
from functools import lru_cache
import time
import sqlite3
from collections import defaultdict
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # In production, use environment variables for this value.

# Set your admin password for dashboard access
ADMIN_PASSWORD = "admin"  # In production, use an environment variable.

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Path to your Excel file
EXCEL_FILE_PATH = 'Item Database/output.xlsx'

# Read the Excel file and force "ItemNumber" to be read as a string
df = pd.read_excel(EXCEL_FILE_PATH, dtype={'ItemNumber': str})

# Clean the "ItemNumber" column: remove any trailing '.0' and extra spaces
df["ItemNumber"] = (
    df["ItemNumber"]
    .str.replace(r'\.0$', '', regex=True)
    .str.strip()
)

# Define Prometheus counters for immediate totals (optional)
lookup_success_counter = Counter("lookup_success_total", "Total number of successful UPC lookups")
lookup_failure_counter = Counter("lookup_failure_total",
                                 "Total number of UPC lookups that did not find an item in the database")
barcode_scan_failure_counter = Counter("barcode_scan_failure_total",
                                       "Total number of barcode decode failures reported from the client")

#########################################
# SQLite-based Historical Logging
#########################################

DATABASE = "metrics.db"


def init_db():
    """Initialize the SQLite database and create the events table if needed."""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT,
            timestamp INTEGER
        )
    """)
    conn.commit()
    conn.close()


def log_event_sql(event_type):
    """Insert an event record into the SQLite database with the current timestamp."""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("INSERT INTO events (event_type, timestamp) VALUES (?, ?)",
              (event_type, int(time.time())))
    conn.commit()
    conn.close()


def get_aggregated_counts():
    """Return total counts for each event type from the SQLite database."""
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    counts = {}
    for event in ["lookup_success", "lookup_failure", "barcode_scan_failure"]:
        c.execute("SELECT COUNT(*) FROM events WHERE event_type = ?", (event,))
        counts[event] = c.fetchone()[0]
    conn.close()
    return counts


# Initialize the database when the app starts
init_db()


#########################################
# Lookup Function (with logging)
#########################################

@lru_cache(maxsize=100)
def lookup_item(barcode_data):
    """
    Look up item name and price in the Excel dataframe based on the SKU.
    Returns (item_name, item_price) or (None, None) if not found.
    """
    barcode_data = str(barcode_data).strip()
    logger.info(f"Attempting lookup for barcode: '{barcode_data}'")

    item_info = df[df["ItemNumber"] == barcode_data]
    if not item_info.empty:
        item_name = item_info["ItemName"].values[0]
        item_price = item_info["ItemPrice"].values[0]
        lookup_success_counter.inc()  # Increment immediate counter
        log_event_sql("lookup_success")  # Log event in SQLite
        logger.info(f"Lookup success: Found '{item_name}' for barcode '{barcode_data}'")
        return item_name, item_price
    else:
        lookup_failure_counter.inc()  # Increment immediate counter
        log_event_sql("lookup_failure")  # Log event in SQLite
        logger.info(f"Lookup failed for barcode '{barcode_data}'")
        return None, None


#########################################
# Routes
#########################################

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        barcode_id = request.form.get("barcode_id")
        logger.info(f"Received POST request with barcode: '{barcode_id}'")
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
    data = request.get_json()
    error = data.get("error", "No error provided")
    details = data.get("details", "")
    barcode_scan_failure_counter.inc()  # Immediate counter increment
    log_event_sql("barcode_scan_failure")  # Log event in SQLite
    logger.error(f"Client error: {error} – {details}")
    return jsonify({"status": "logged"}), 200


@app.route("/metrics")
def metrics():
    # Expose Prometheus-format metrics (immediate totals)
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


#########################################
# Historical Data API Endpoint (SQLite)
#########################################

@app.route("/api/historical")
def historical_data():
    """
    Query the SQLite database to return aggregated counts for a given event type
    over the past 30 days. Use a query parameter 'group_by' to specify the granularity:
    'minute' (format: YYYY-MM-DD HH:MM:00) or default 'hour' (format: YYYY-MM-DD HH:00:00).
    Timestamps are converted to local time.
    """
    event_type = request.args.get("event_type")
    if not event_type:
        return jsonify({"error": "event_type parameter required"}), 400

    group_by = request.args.get("group_by", "hour")
    if group_by == "minute":
        time_format = '%Y-%m-%d %H:%M:00'
    else:
        time_format = '%Y-%m-%d %H:00:00'

    # Calculate threshold for the past 30 days
    threshold = int(time.time()) - 30 * 24 * 3600

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    # Convert the UNIX timestamp to local time using the 'localtime' modifier.
    query = f"""
        SELECT strftime('{time_format}', datetime(timestamp, 'unixepoch', 'localtime')) as time_group, COUNT(*) as count
        FROM events
        WHERE event_type = ? AND timestamp >= ?
        GROUP BY time_group
        ORDER BY time_group ASC
    """
    c.execute(query, (event_type, threshold))
    rows = c.fetchall()
    conn.close()

    result = [{"hour": row[0], "count": row[1]} for row in rows]
    return jsonify(result)


#########################################
# Dashboard (Password Protected)
#########################################

@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    # If admin is not logged in, show password prompt.
    if "admin" not in session:
        if request.method == "POST":
            password = request.form.get("password")
            if password == ADMIN_PASSWORD:
                session["admin"] = True
                return redirect(url_for("dashboard"))
            else:
                flash("Incorrect password. Please try again.", "error")
        return render_template("admin_login.html")

    # Admin is authenticated; get aggregated counts from the SQLite database.
    counts = get_aggregated_counts()
    metrics_data = {
        "lookup_success_total": counts.get("lookup_success", 0),
        "lookup_failure_total": counts.get("lookup_failure", 0),
        "barcode_scan_failure_total": counts.get("barcode_scan_failure", 0)
    }
    return render_template("dashboard.html", metrics=metrics_data)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
