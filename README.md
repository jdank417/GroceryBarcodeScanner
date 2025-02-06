# THIS BRANCH IS TIED TO OUR RENDER ENVIRONMENT; DO NOT PUSH TO HERE UNLESS YOU ARE INTENDING ON DEPLOYING TO PRODUCTION

# Branch Rules are in Effect

# Barcode Scanner & Metrics Dashboard

A full-stack application that lets you scan barcodes, perform lookups from an Excel-based inventory, and view both real-time and historical metrics—all backed by Flask, Pandas, and SQLite, with a slick QuaggaJS-powered front end.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API & Endpoints](#api--endpoints)
- [Frontend Details](#frontend-details)
  - [Barcode Scanner Interface](#barcode-scanner-interface)
  - [Admin Login Page](#admin-login-page)
- [Logging & Metrics](#logging--metrics)
- [Deployment on Render](#deployment-on-render)
- [License](#license)

## Overview

This project provides a user-friendly barcode scanner app built for college students and professionals alike. It leverages an Excel file as a lookup source for item details, logs events in SQLite, and exposes both real-time (via Prometheus) and historical metrics. The application also features a password-protected admin dashboard.

## Features

- **Barcode Lookup:**  
  Scan or manually enter a barcode (SKU) to fetch item details (name and price) from an Excel file.

- **Native Camera Support:**  
  Trigger the device's native camera to capture a barcode image and decode it using QuaggaJS.

- **Real-Time Metrics:**  
  Prometheus counters track lookup successes, lookup failures, and barcode scan errors.

- **Historical Logging:**  
  Persist all events to a SQLite database and expose an API endpoint for aggregating historical data (last 30 days).

- **Admin Dashboard:**  
  Secure dashboard (protected by an admin password) to view historical metrics.

- **Responsive UI:**  
  Modern, responsive front end using HTML, CSS, and JavaScript.

## Architecture

- **Backend:**  
  - **Flask:** Serves web pages, API endpoints, and handles barcode lookups.
  - **Pandas:** Reads and cleans the Excel inventory data.
  - **SQLite:** Stores persistent event logs.
  - **Prometheus Client:** Exposes real-time metrics at the `/metrics` endpoint.

- **Frontend:**  
  - **Barcode Scanner Interface:**  
    - Built with HTML, CSS, and JavaScript.
    - Uses QuaggaJS (via CDN) for barcode decoding.
  - **Admin Login Page:**  
    - A secure, simple form for administrator authentication.

## Prerequisites

- **Python 3.7+**
- **Pip** or another package manager
- Python packages required:
  - `Flask`
  - `pandas`
  - `prometheus_client`
  - `openpyxl` (for Excel support)
  - _Plus standard libraries (e.g., `sqlite3`, `logging`, etc.)_

## Installation

1. **Clone the Repository**

   ```bash
   git clone https://github.com/jdank417/GroceryBarcodeScanner.git
   cd GroceryBarcodeScanner
   ```

2. **Set Up a Virtual Environment & Install Dependencies**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   pip install -r requirements.txt
   ```

3. **Place the Excel File**

   Ensure your Excel file (e.g., `output.xlsx`) is located at:

   ```
   Item Database/output.xlsx
   ```

4. **Initialize the SQLite Database**

   The SQLite database (`metrics.db`) is automatically initialized on application start.

## Configuration

- **Secret Key & Admin Password:**  
  The Flask secret key and admin password are hard-coded in the application (in `app.py`) for demonstration purposes.  
  **Note:** In production, set these values via environment variables or a secure configuration file.

- **Excel File Path:**  
  Adjust the `EXCEL_FILE_PATH` variable in `app.py` if your Excel file is stored in a different location.

## Usage

1. **Run the Flask Application**

   ```bash
   python app.py
   ```

2. **Access the Application**

   - **Barcode Scanner Interface:**  
     Navigate to [http://localhost:8000](http://localhost:8000) to access the main page where you can enter a barcode manually or use the native camera to scan one.
     
   - **Admin Dashboard:**  
     Navigate to [http://localhost:8000/dashboard](http://localhost:8000/dashboard) to access the admin login page.  
     Enter the admin password (default is `admin`) to view historical metrics.

## API & Endpoints

- **`/`**  
  - **Methods:** GET, POST  
  - **Description:**  
    Main page for barcode lookup. Submits a barcode via form data and displays lookup results.

- **`/log_client_error`**  
  - **Method:** POST  
  - **Description:**  
    API endpoint to log client-side barcode decoding errors. Returns a JSON response confirming the error was logged.

- **`/metrics`**  
  - **Method:** GET  
  - **Description:**  
    Exposes real-time metrics in Prometheus format.

- **`/api/historical`**  
  - **Method:** GET  
  - **Description:**  
    Returns aggregated historical counts for a specified event type (e.g., `lookup_success`, `lookup_failure`, `barcode_scan_failure`).  
    Accepts query parameters:
    - `event_type`: Required, one of the event types.
    - `group_by`: Optional, can be `minute` or `hour` (default).

- **`/dashboard`**  
  - **Methods:** GET, POST  
  - **Description:**  
    Password-protected admin dashboard displaying historical metrics from SQLite.

## Frontend Details

### Barcode Scanner Interface

- **File:** `index.html`
- **Overview:**  
  This is the primary user interface where users can:
  - **Enter a Barcode:**  
    - A text input for manual barcode entry.
    - A submit button for initiating the lookup.
  - **Scan a Barcode:**  
    - A button to trigger the device’s native camera.
    - Uses a hidden file input with `capture=camera` for mobile devices.
    - Processes the captured image using QuaggaJS to decode the barcode.
  - **Display Results:**  
    - Flash messages for success or error.
    - If a valid item is found, it shows the item name, price, and optionally a processed image.
  - **Additional Sections:**  
    - **About Section:** Provides context about the application.
    - **Contact Section:** Lists contact information for the development team.
  - **Styling:**  
    - Custom CSS provides a modern and responsive look.
  - **JavaScript:**  
    - Handles camera capture, barcode decoding, and error reporting to the backend via `/log_client_error`.

### Admin Login Page

- **File:** `admin_login.html`
- **Overview:**  
  A secure login page for administrators.  
  - **Password Input:**  
    A form field for the admin password.
  - **Flash Messages:**  
    Displays error messages if authentication fails.
  - **Design:**  
    Minimalist design with simple styling for clarity.

## Logging & Metrics

- **Immediate Metrics (Prometheus):**  
  - **Counters:**  
    - `lookup_success_total`: Successful barcode lookups.
    - `lookup_failure_total`: Failed barcode lookups.
    - `barcode_scan_failure_total`: Barcode decoding failures.
  - **Endpoint:**  
    Available at `/metrics`.

- **Historical Logging (SQLite):**  
  - **Logging:**  
    Events are logged in `metrics.db` using functions such as `log_event_sql()`.
  - **API:**  
    The `/api/historical` endpoint aggregates event counts over the past 30 days, with options for minute or hour granularity.

## Deployment on Render

1. **Create a New Web Service:**  
   - Go to [Render](https://render.com/) and create a new web service.

2. **Connect Your Repository:**  
   - Connect your GitHub repository containing this project.

3. **Set Build & Start Commands:**  
   - **Build Command:**  
     ```bash
     pip install -r requirements.txt
     ```
   - **Start Command:**  
     ```bash
     gunicorn app:app --bind 0.0.0.0:$PORT
     ```

4. **Deploy and Access:**  
   - Render will automatically deploy and provide a live URL where the app is accessible.

## License

Distributed under the MIT License. See [LICENSE](LICENSE) for more information.

