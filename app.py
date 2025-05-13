"""
GroceryBarcodeScanner - Barcode Scanning Software
Copyright (c) 2024 Jason Dank

This software is licensed under the End User License Agreement (EULA).
Unauthorized use, distribution, or modification is strictly prohibited.

By using this software, you agree to the terms outlined in the EULA.
For more details, refer to the EULA or contact Jason Dank at jasondank@yahoo.com.

"""



import io
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
import glob
from werkzeug.utils import secure_filename

# For potential image conversion and creating dummy images
try:
    from PIL import Image
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    Image = None

# New imports for server‐side barcode detection
try:
    import cv2
    import numpy as np
    from pyzbar.pyzbar import decode as decode_barcode
    import base64
except ImportError:
    cv2 = None

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Use environment variables in production.

ADMIN_PASSWORD = "admin"  # Also use environment variables in production.

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define your upload folder (inside your static folder)
UPLOAD_FOLDER = os.path.join(app.static_folder, "uploads")
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
    app.logger.info(f"Created UPLOAD_FOLDER at {UPLOAD_FOLDER}")

# Path to your Excel file
EXCEL_FILE_PATH = 'Item Database/output.xlsx'
df = pd.read_excel(EXCEL_FILE_PATH, dtype={'ItemNumber': str})
df["ItemNumber"] = df["ItemNumber"].str.replace(r'\.0$', '', regex=True).str.strip()

# Prometheus counters
lookup_success_counter = Counter("lookup_success_total", "Total successful UPC lookups")
lookup_failure_counter = Counter("lookup_failure_total", "Total UPC lookups that did not find an item")
barcode_scan_failure_counter = Counter("barcode_scan_failure_total", "Total barcode decode failures reported by client")
non_numerical_value_counter = Counter("non_numerical_value_total",
                                      "Total non numerical SKU inputs that were sanitized to an empty string")

DATABASE = "metrics.db"


def init_db():
    """
    Initialize the SQLite database.
    This function now only creates the table if it does not exist,
    preserving existing data.
    """
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
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
        lookup_success_counter.inc()
        log_event_sql("lookup_success", sku=barcode_data, item_name=item_name)
        return item_name, item_price
    else:
        lookup_failure_counter.inc()
        log_event_sql("lookup_failure", sku=barcode_data, item_name=None)
        return None, None


def sanitize_sku(sku):
    """
    Sanitizes the SKU input to ensure it contains only digits and no spaces.
    """
    sku = str(sku).strip()
    return re.sub(r'\D', '', sku)


def write_file(file_obj, save_path):
    """
    Write the contents of file_obj to save_path.
    If file_obj has a 'save' method, use that; otherwise, write its contents.
    """
    if hasattr(file_obj, "save"):
        file_obj.seek(0)
        file_obj.save(save_path)
    else:
        with open(save_path, "wb") as f:
            f.write(file_obj.getvalue())


def save_failed_image(file):
    """
    Saves an uploaded image file as the latest failed image.
    Removes any existing file starting with "latest_failed_image" from the UPLOAD_FOLDER.
    Supports multiple image types (including HEIC/HEIF conversion to JPEG if possible).
    Returns a tuple: (saved_filename, full_save_path)
    """
    pattern = os.path.join(UPLOAD_FOLDER, "latest_failed_image*")
    for existing_file in glob.glob(pattern):
        os.remove(existing_file)
        app.logger.info(f"Removed existing failed image: {existing_file}")

    original_filename = secure_filename(file.filename)
    _, ext = os.path.splitext(original_filename)
    ext = ext.lower() if ext else ".jpg"
    app.logger.info(f"Original filename: {original_filename}, extension: {ext}")

    saved_filename = None
    save_path = None

    if ext in [".heic", ".heif"] and Image is not None:
        try:
            image = Image.open(file)
            saved_filename = "latest_failed_image.jpg"
            save_path = os.path.join(UPLOAD_FOLDER, saved_filename)
            image.save(save_path, "JPEG")
            app.logger.info(f"Converted HEIC image and saved to {save_path}")
        except Exception as e:
            app.logger.error(f"HEIC conversion failed: {e}. Saving original file.")
            saved_filename = "latest_failed_image" + ext
            save_path = os.path.join(UPLOAD_FOLDER, saved_filename)
            file.seek(0)
            write_file(file, save_path)
    else:
        saved_filename = "latest_failed_image" + ext
        save_path = os.path.join(UPLOAD_FOLDER, saved_filename)
        file.seek(0)
        write_file(file, save_path)
        app.logger.info(f"Saved failed image to {save_path}")

    return saved_filename, save_path


@app.route("/", methods=["GET", "POST"])
def index():
    """
    Main page for manual barcode lookups and product name searches.
    """
    if request.method == "POST":
        query = request.form.get("barcode_id")
        if query:
            query = query.strip()
            if query.isdigit():
                sanitized_barcode = sanitize_sku(query)
                if not sanitized_barcode:
                    non_numerical_value_counter.inc()
                    log_event_sql("non_numerical_value", sku=query, item_name="Non numerical value")
                    flash("Non numerical SKU input provided.", "error")
                    return render_template("index.html")
                item_name, item_price = lookup_item(sanitized_barcode)
                if item_name and item_price:
                    flash(f"Item: {item_name}, Price: ${item_price}", "info")
                else:
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
                matches = df[df["ItemName"].str.contains(query, case=False, na=False)]
                if not matches.empty:
                    top_matches = matches.head(5)
                    results_html = "<ul>"
                    results_list = []
                    for _, row in top_matches.iterrows():
                        results_html += f"<li>{row['ItemName']} (UPC: {row['ItemNumber']}) - Price: ${row['ItemPrice']}</li>"
                        results_list.append(
                            f"{row['ItemName']} (UPC: {row['ItemNumber']}) - Price: ${row['ItemPrice']}")
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


@app.route("/process_barcode_image", methods=["POST"])
def process_barcode_image():
    """
    Endpoint to process an uploaded barcode image.
    If barcode detection fails, the image is saved and replaces any previously stored image.
    """
    if 'barcode_image' not in request.files:
        flash("No file part in the request.", "error")
        return redirect(url_for("index"))
    file = request.files['barcode_image']
    if file.filename == "":
        flash("No file selected.", "error")
        return redirect(url_for("index"))
    if not file.content_type.startswith("image/"):
        flash("Uploaded file is not an image.", "error")
        return redirect(url_for("index"))

    saved_filename, save_path = save_failed_image(file)
    file.seek(0)
    barcode_found = process_barcode_image(file)
    if not barcode_found:
        if os.path.exists(save_path):
            file_size = os.path.getsize(save_path)
            app.logger.info(f"Confirmed saved failed image at {save_path} ({file_size} bytes)")
        else:
            app.logger.error("Failed to save the failed image!")
        flash("Barcode not detected. Latest failed image saved for debugging.", "error")
    else:
        flash("Barcode detected successfully!", "success")
    return redirect(url_for("dashboard"))


@app.route("/log_client_error", methods=["POST"])
def log_client_error():
    """
    Log client errors such as barcode scan failures.
    If a file is included in the request (multipart/form-data), save it as the latest failed image.
    If no file is provided, create a dummy image so that the failed image is updated.
    """
    if 'barcode_image' in request.files:
        file = request.files['barcode_image']
        saved_filename, save_path = save_failed_image(file)
        if os.path.exists(save_path):
            file_size = os.path.getsize(save_path)
            app.logger.info(f"Saved failed image from log_client_error to {save_path} ({file_size} bytes)")
        else:
            app.logger.error("Failed to save the failed image from log_client_error!")
    else:
        # No file provided; create a dummy image.
        if Image is not None:
            try:
                dummy_image = Image.new("RGB", (300, 300), color=(255, 0, 0))
                dummy_file = io.BytesIO()
                dummy_image.save(dummy_file, "JPEG")
                dummy_file.seek(0)
                dummy_file.filename = "dummy_failed_image.jpg"
                dummy_file.content_type = "image/jpeg"
                saved_filename, save_path = save_failed_image(dummy_file)
                if os.path.exists(save_path):
                    file_size = os.path.getsize(save_path)
                    app.logger.info(f"Created dummy failed image for testing at {save_path} ({file_size} bytes)")
                else:
                    app.logger.error("Failed to create dummy failed image!")
            except Exception as e:
                app.logger.error(f"Error creating dummy image: {e}")
        else:
            app.logger.error("Pillow not available to create dummy image")

    data = request.get_json(silent=True)
    if data is None:
        data = {}
    error = data.get("error", "No error provided")
    details = data.get("details", "")
    sku = data.get("sku", None)

    barcode_scan_failure_counter.inc()
    log_event_sql("barcode_scan_failure", sku=sku, item_name=details)

    app.logger.error(f"Client error: {error} – {details}")
    return jsonify({"status": "logged"}), 200


@app.route("/detect_barcode_region", methods=["POST"])
def detect_barcode_region():
    """
    Processes an uploaded image, detects the barcode region using pyzbar,
    expands the detected region by a margin to include surrounding packaging,
    crops the image to that expanded bounding box, and returns the cropped image (base64-encoded)
    along with the bounding box coordinates.
    """
    if 'barcode_image' not in request.files:
        return jsonify({"error": "No image file provided"}), 400
    file = request.files["barcode_image"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400
    if cv2 is None:
        return jsonify({"error": "OpenCV is not available"}), 500

    # Read image bytes and decode with OpenCV.
    file_bytes = np.frombuffer(file.read(), np.uint8)
    img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    if img is None:
        return jsonify({"error": "Could not decode image"}), 400

    barcodes = decode_barcode(img)
    if not barcodes:
        return jsonify({"error": "No barcode detected"}), 200

    # For simplicity, take the first detected barcode.
    barcode = barcodes[0]
    # Use .left and .top for coordinates.
    x, y, w, h = barcode.rect.left, barcode.rect.top, barcode.rect.width, barcode.rect.height

    # Expand the region by a margin (10% of width and height)
    margin_w = int(0.25 * w)
    margin_h = int(0.25 * h)
    x_new = max(0, x - margin_w)
    y_new = max(0, y - margin_h)
    x_end = min(img.shape[1], x + w + margin_w)
    y_end = min(img.shape[0], y + h + margin_h)

    cropped = img[y_new:y_end, x_new:x_end]

    # Encode the cropped image to JPEG and then to base64.
    retval, buffer = cv2.imencode('.jpg', cropped)
    jpg_as_text = base64.b64encode(buffer).decode('utf-8')

    return jsonify({
        "cropped_image": jpg_as_text,
        "bounding_box": {"x": x_new, "y": y_new, "w": x_end - x_new, "h": y_end - y_new}
    })




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
    Admin-protected dashboard. Displays aggregated metrics and a collapsible section
    for the latest failed barcode image (if available).
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

    # Look for the latest failed image.
    latest_failed_image = None
    latest_failed_timestamp = None
    pattern = os.path.join(UPLOAD_FOLDER, "latest_failed_image*")
    files = glob.glob(pattern)
    app.logger.info(f"Dashboard lookup: searching for files with pattern {pattern}. Found: {files}")
    if files:
        file_path = files[0]
        latest_failed_image = os.path.basename(file_path)
        mtime = os.path.getmtime(file_path)
        latest_failed_timestamp = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
    else:
        app.logger.info("No latest failed image file found in uploads folder.")

    return render_template("dashboard.html", metrics=metrics_data,
                           latest_failed_image=latest_failed_image,
                           latest_failed_timestamp=latest_failed_timestamp)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
