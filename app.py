# app.py
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

# Admin password (use environment variables in production)
ADMIN_PASSWORD = "admin"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Path to your Excel file and DataFrame setup
EXCEL_FILE_PATH = 'Item Database/output.xlsx'
df = pd.read_excel(EXCEL_FILE_PATH, dtype={'ItemNumber': str})
df["ItemNumber"] = df["ItemNumber"].str.replace(r'\.0$', '', regex=True).str.strip()

# Prometheus counters for immediate totals
lookup_success_counter = Counter("lookup_success_total", "Total number of successful UPC lookups")
lookup_failure_counter = Counter("lookup_failure_total", "Total number of UPC lookups that did not find an item in the database")
barcode_scan_failure_counter = Counter("barcode_scan_failure_total", "Total number of barcode decode failures reported from the client")

# SQLite-based logging for historical data
DATABASE = "metrics.db"

def init_db():
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
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("INSERT INTO events (event_type, timestamp) VALUES (?, ?)",
              (event_type, int(time.time())))
    conn.commit()
    conn.close()

def get_aggregated_counts():
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
    barcode_data = str(barcode_data).strip()
    logger.info(f"Attempting lookup for barcode: '{barcode_data}'")
    item_info = df[df["ItemNumber"] == barcode_data]
    if not item_info.empty:
        item_name = item_info["ItemName"].values[0]
        item_price = item_info["ItemPrice"].values[0]
        lookup_success_counter.inc()
        log_event_sql("lookup_success")
        logger.info(f"Lookup success: Found '{item_name}' for barcode '{barcode_data}'")
        return item_name, item_price
    else:
        lookup_failure_counter.inc()
        log_event_sql("lookup_failure")
        logger.info(f"Lookup failed for barcode '{barcode_data}'")
        return None, None

# Traditional route using server-rendered HTML (if needed)
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
    barcode_scan_failure_counter.inc()
    log_event_sql("barcode_scan_failure")
    logger.error(f"Client error: {error} – {details}")
    return jsonify({"status": "logged"}), 200

@app.route("/metrics")
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

@app.route("/api/historical")
def historical_data():
    event_type = request.args.get("event_type")
    if not event_type:
        return jsonify({"error": "event_type parameter required"}), 400
    group_by = request.args.get("group_by", "hour")
    if group_by == "minute":
        time_format = '%Y-%m-%d %H:%M:00'
    else:
        time_format = '%Y-%m-%d %H:00:00'
    threshold = int(time.time()) - 30 * 24 * 3600
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
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

@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
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
    metrics_data = {
        "lookup_success_total": counts.get("lookup_success", 0),
        "lookup_failure_total": counts.get("lookup_failure", 0),
        "barcode_scan_failure_total": counts.get("barcode_scan_failure", 0)
    }
    return render_template("dashboard.html", metrics=metrics_data)

# New API endpoints for the React SPA

@app.route("/api/lookup", methods=["POST"])
def api_lookup():
    data = request.get_json()
    barcode_id = data.get("barcode_id", "").strip()
    if not barcode_id:
        return jsonify({"error": "Please provide a barcode ID."}), 400
    item_name, item_price = lookup_item(barcode_id)
    if item_name and item_price:
        return jsonify({
            "item_name": item_name,
            "item_price": item_price
        })
    else:
        return jsonify({"error": "Item not found"}), 404

@app.route("/api/admin/login", methods=["POST"])
def api_admin_login():
    data = request.get_json()
    password = data.get("password", "")
    if password == ADMIN_PASSWORD:
        session["admin"] = True
        return jsonify({"success": True})
    else:
        return jsonify({"error": "Invalid password"}), 401

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
