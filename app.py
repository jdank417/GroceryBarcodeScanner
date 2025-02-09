from flask import Flask, render_template, request, flash, session, redirect, url_for, Response, jsonify
from markupsafe import Markup
import pandas as pd
import os
import logging
from functools import lru_cache
import time
import sqlite3
import datetime
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import re  # For SKU sanitization
import difflib  # For fuzzy matching of UPCs

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
non_numerical_value_counter = Counter("non_numerical_value_total", "Total non numerical SKU inputs that were sanitized to an empty string")

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

init_db()

def log_event_sql(event_type, sku=None, item_name=None):
    """
    Synchronously log an event to the SQLite DB, including optional SKU and item name.
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
    for event in [
        "lookup_success",
        "lookup_failure",
        "barcode_scan_failure",
        "non_numerical_value",
        "search_product_success",
        "search_product_failure"
    ]:
        c.execute("SELECT COUNT(*) FROM events WHERE event_type = ?", (event,))
        counts[event] = c.fetchone()[0]
    conn.close()
    return counts

@lru_cache(maxsize=100)
def lookup_item(barcode_data):
    """
    Look up the item in the Excel DataFrame by SKU.
    If found, increment success counters and log the success with SKU + item_name.
    Otherwise, log a failure with the UPC.
    """
    barcode_data = str(barcode_data).strip()
    item_info = df[df["ItemNumber"] == barcode_data]
    if not item_info.empty:
        item_name = item_info["ItemName"].values[0]
        item_price = item_info["ItemPrice"].values[0]
        # Log successful lookup
        lookup_success_counter.inc()
        log_event_sql("lookup_success", sku=barcode_data, item_name=item_name)
        return item_name, item_price
    else:
        # Log lookup failure
        lookup_failure_counter.inc()
        log_event_sql("lookup_failure", sku=barcode_data, item_name=None)
        return None, None

def sanitize_sku(sku):
    """
    Sanitizes the SKU input to ensure it contains only digits and no spaces.
    - Converts the input to a string.
    - Strips leading/trailing whitespace.
    - Removes all non-digit characters.
    """
    sku = str(sku).strip()  # Remove leading/trailing whitespace
    sanitized = re.sub(r'\D', '', sku)  # Remove any non-digit characters
    return sanitized

@app.route("/", methods=["GET", "POST"])
def index():
    """
    Main page for manual barcode lookups and product name searches.
    For UPC searches, if no exact match is found, returns 5 similar UPC suggestions.
    """
    if request.method == "POST":
        query = request.form.get("barcode_id")
        if query:
            query = query.strip()
            # Check if the query is all digits (UPC search)
            if query.isdigit():
                sanitized_barcode = sanitize_sku(query)
                if not sanitized_barcode:
                    non_numerical_value_counter.inc()
                    log_event_sql("non_numerical_value", sku=query, item_name="Non numerical value")
                    flash("Non numerical SKU input provided.", "error")
                    return render_template("index.html")
                # Attempt to look up the UPC
                item_name, item_price = lookup_item(sanitized_barcode)
                if item_name and item_price:
                    flash(f"Item: {item_name}, Price: ${item_price}", "info")
                else:
                    # If no exact match, suggest 5 similar UPC's from the database.
                    possible_upcs = df["ItemNumber"].tolist()
                    suggestions = difflib.get_close_matches(sanitized_barcode, possible_upcs, n=5, cutoff=0.6)
                    if suggestions:
                        results_html = "<ul>"
                        for upc in suggestions:
                            suggestion = df[df["ItemNumber"] == upc].iloc[0]
                            results_html += f"<li>{suggestion['ItemName']} (UPC: {upc}) - Price: ${suggestion['ItemPrice']}</li>"
                        results_html += "</ul>"
                        flash(Markup("Item not found. Did you mean one of these?<br>" + results_html), "warning")
                    else:
                        flash("Item not found in the Excel file.", "warning")
            else:
                # Treat as product name search
                matches = df[df["ItemName"].str.contains(query, case=False, na=False)]
                if not matches.empty:
                    top_matches = matches.head(5)
                    results_html = "<ul>"
                    results_list = []
                    for _, row in top_matches.iterrows():
                        results_html += f"<li>{row['ItemName']} (UPC: {row['ItemNumber']}) - Price: ${row['ItemPrice']}</li>"
                        results_list.append(f"{row['ItemName']} (UPC: {row['ItemNumber']}) - Price: ${row['ItemPrice']}")
                    results_html += "</ul>"
                    results_summary = "; ".join(results_list)
                    log_event_sql("search_product_success", sku=query, item_name=results_summary)
                    flash(Markup(results_html), "info")
                else:
                    log_event_sql("search_product_failure", sku=query, item_name="No matches found")
                    flash("No products found matching your search.", "warning")
        else:
            flash("Please enter a valid UPC or product name.", "error")
    return render_template("index.html")

@app.route("/log_client_error", methods=["POST"])
def log_client_error():
    """
    Log client errors such as barcode scan failures.
    """
    data = request.get_json()
    error = data.get("error", "No error provided")
    details = data.get("details", "")
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
    Expected format: an array of objects with keys "hour" and "count".
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
        end_dt = end_dt + datetime.timedelta(days=1) - datetime.timedelta(seconds=1)
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

    start_ts = int(start_dt.timestamp())
    end_ts = int(end_dt.timestamp())

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    query = """
        SELECT event_type, timestamp, sku, item_name
        FROM events
        WHERE event_type IN (
            'lookup_success', 
            'lookup_failure', 
            'search_product_success', 
            'search_product_failure',
            'barcode_scan_failure'
        )
          AND timestamp >= ?
          AND timestamp <= ?
        ORDER BY timestamp ASC
    """
    c.execute(query, (start_ts, end_ts))
    rows = c.fetchall()
    conn.close()

    def aggregate_events(rows):
        agg = {}
        for etype, ts, sku, iname in rows:
            dt = datetime.datetime.fromtimestamp(ts)
            hour_str = dt.strftime("%Y-%m-%d %H:00:00")
            agg[hour_str] = agg.get(hour_str, 0) + 1
        return [{"hour": k, "count": v} for k, v in agg.items()]

    filtered = [row for row in rows if row[0] == event_type]
    aggregated = aggregate_events(filtered)
    return jsonify(aggregated)

@app.route("/api/item_events", endpoint="item_events")
def item_events():
    """
    Return a list of success/failure events with their time, sku, and item_name,
    for a given date range (default last 7 days).
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
        WHERE event_type IN (
            'lookup_success', 
            'lookup_failure', 
            'search_product_success', 
            'search_product_failure',
            'barcode_scan_failure'
        )
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
    Admin-protected dashboard. Shows aggregated metrics and a chart of hourly data for each event type + item-level events.
    The Successful Lookups count is a combination of lookup_success and search_product_success,
    and the Lookup Failures count is a combination of lookup_failure and search_product_failure.
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

    counts = get_aggregated_counts()
    lookup_success_count = counts.get("lookup_success", 0)
    search_product_success_count = counts.get("search_product_success", 0)
    combined_success = lookup_success_count + search_product_success_count

    lookup_failure_count = counts.get("lookup_failure", 0)
    search_product_failure_count = counts.get("search_product_failure", 0)
    combined_failure = lookup_failure_count + search_product_failure_count

    barcode_failure_count = counts.get("barcode_scan_failure", 0)
    total = combined_success + combined_failure
    success_rate = (combined_success / total) * 100 if total else 0

    metrics_data = {
        "lookup_success_total": combined_success,
        "lookup_failure_total": combined_failure,
        "barcode_scan_failure_total": barcode_failure_count,
        "success_rate": round(success_rate, 2)
    }
    return render_template("dashboard.html", metrics=metrics_data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
