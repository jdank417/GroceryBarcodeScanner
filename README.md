# THIS BRANCH IS TIED TO OUR RENDER ENVIRONMENT; DO NOT PUSH TO HERE UNLESS YOU ARE INTENDING ON DEPLOYING TO PRODUCTION

# Branch Rules are in Effect

# Barcode Scanner & Metrics Dashboard

A full-stack application that lets you scan barcodes, perform lookups from a robust SQLite database, upload Excel files through an admin interface, and view both real-time and historical metrics—all backed by Flask, Pandas, and SQLite, with a modern, responsive UI powered by QuaggaJS.

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
  Scan or manually enter a barcode (SKU) to fetch item details (name and price) from a SQLite database.

- **Native Camera Support:**  
  Trigger the device's native camera to capture a barcode image and decode it using QuaggaJS.

- **ML-Based Barcode Detection:**  
  Leverage machine learning and computer vision (OpenCV, pyzbar, TensorFlow) to enhance barcode detection accuracy by pre-processing images before decoding.

- **Excel File Upload:**  
  Upload Excel files through the admin dashboard to update the product database. Supports various column formats and automatic mapping.

- **Multiple UPC Support:**  
  Handle products with multiple barcodes using comma-separated values. Each barcode is stored separately in the database with the same product details.

- **Robust Database Structure:**  
  Store product data in SQLite for improved performance and reliability compared to direct Excel file reading.

- **Real-Time Metrics:**  
  Prometheus counters track lookup successes, lookup failures, and barcode scan errors.

- **Historical Logging:**  
  Persist all events to a SQLite database and expose API endpoints for aggregating historical data.

- **Interactive Admin Dashboard:**  
  Secure dashboard with metrics visualization, data filtering, and product database management.

- **Modern UI:**  
  Responsive, user-friendly interface with dark/light mode support, animations, and consistent design across all pages.

- **Drag-and-Drop File Upload:**  
  Intuitive drag-and-drop interface for Excel file uploads with visual feedback.

## Architecture

- **Backend:**  
  - **Flask:** Serves web pages, API endpoints, and handles barcode lookups.
  - **Pandas:** Processes Excel files for database updates and data cleaning.
  - **SQLite:** 
    - Stores product data in the `products` table for efficient lookups.
    - Logs events in the `events` table for historical analysis.
  - **Prometheus Client:** Exposes real-time metrics at the `/metrics` endpoint.
  - **Machine Learning & Computer Vision:**
    - **OpenCV:** Processes images for barcode detection and preprocessing.
    - **pyzbar:** Detects and decodes barcodes from images.
    - **TensorFlow/Keras:** Provides advanced image processing capabilities.
    - **Server-side Barcode Detection:** Pre-processes images to improve QuaggaJS accuracy:
      - Detects barcode regions in uploaded images
      - Expands detected regions to include surrounding context
      - Crops images to focus on barcode areas
      - Returns optimized images to the client for final decoding

- **Frontend:**  
  - **Modern CSS Framework:**
    - Custom-built modern.css for consistent styling across all pages.
    - Responsive design with mobile-first approach.
    - Dark/light mode support with theme persistence.
    - Animation and transition effects for better user experience.
  
  - **Barcode Scanner Interface:**  
    - Built with HTML, CSS, and JavaScript.
    - Uses QuaggaJS for barcode decoding.
    - Camera integration for mobile and desktop devices.
    - Real-time feedback with visual indicators.
  
  - **Admin Dashboard:**
    - Interactive metrics visualization with Chart.js.
    - Excel file upload with drag-and-drop support.
    - Data filtering and date range selection.
    - Product database management interface.
  
  - **Admin Login Page:**  
    - Secure authentication with password protection.
    - Modern, branded login experience.
    - Error handling with visual feedback.

## Prerequisites

- **Python 3.7+**
- **Pip** or another package manager
- Python packages required:
  - `Flask`
  - `pandas`
  - `prometheus_client`
  - `openpyxl` (for Excel support)
  - **ML & Computer Vision:**
    - `opencv-python`
    - `pyzbar`
    - `tensorflow`
    - `keras`
    - `numpy`
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

- **Database Initialization:**  
  The SQLite database (`metrics.db`) is automatically initialized on application start. It creates two main tables:
  - `events`: Stores all application events (lookups, searches, errors)
  - `products`: Stores product data imported from Excel files

- **Initial Data Loading:**  
  If the products table is empty on startup, the application will attempt to load initial data from the Excel file at `Item Database/output2.xlsx`. This behavior can be modified in the `load_initial_data()` function.

- **Styling Customization:**  
  The application uses a custom CSS file (`static/css/modern.css`) for styling. You can modify this file to customize the appearance of the application.

## Usage

1. **Run the Flask Application**

   ```bash
   python app.py
   ```

2. **Access the Application**

   - **Barcode Scanner Interface:**  
     Navigate to [http://localhost:8000](http://localhost:8000) to access the main page where you can:
     - Enter a barcode manually
     - Search for products by name
     - Use your device's camera to scan barcodes
     - Toggle between light and dark themes

   - **Admin Dashboard:**  
     Navigate to [http://localhost:8000/dashboard](http://localhost:8000/dashboard) to access the admin login page.  
     Enter the admin password (default is `admin`) to access the dashboard where you can:
     - View application metrics and statistics
     - Upload Excel files to update the product database
     - View detailed event logs
     - Analyze failed barcode scans
     - Filter data by date range

3. **Uploading Excel Files**

   The system supports various Excel formats with flexible column mapping:
   
   - Upload files through the drag-and-drop interface on the admin dashboard
   - The system automatically maps columns based on common naming patterns
   - Supported column types include:
     - Product IDs: "Product Code", "Barcode", "UPC", "SKU", "ItemNumber"
     - Product Names: "Product Name", "Name", "Description", "ItemName"
     - Prices: "Price", "Cost", "Retail Price", "ItemPrice"
   - Multiple UPCs can be included in a single cell using comma-separated values
   - The system provides detailed feedback on the upload process

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
  A modern, user-friendly interface for barcode scanning and product lookups:
  
  - **Responsive Navigation:**
    - Modern navbar with app branding and navigation links
    - Dark/light mode toggle with theme persistence
    - Mobile-responsive design with collapsible menu
  
  - **Manual Entry:**  
    - Enhanced text input with icon and visual feedback
    - Improved submit button with icon and hover effects
    - Support for both UPC lookup and product name search
  
  - **Camera Scanning:**  
    - Prominent scan button with camera icon
    - Visual feedback during scanning process
    - Preview of captured and processed images
    - Error handling with helpful messages
  
  - **Results Display:**  
    - Animated alerts with appropriate icons for different message types
    - Categorized messages (success, warning, error)
    - Suggestions for similar products when exact match not found
  
  - **Information Sections:**  
    - Redesigned About section with technology icons and mission statement
    - Enhanced Contact section with visual organization of team members
    - Key Features list highlighting app capabilities
  
  - **Modern Footer:**
    - Multi-column layout with project information
    - Quick links to different sections
    - Technology links with icons
    - Social media and contact links
  
  - **Visual Enhancements:**
    - Card-based layout with hover effects and shadows
    - Consistent color scheme using CSS variables
    - Smooth animations and transitions
    - Background image that changes with theme

### Admin Dashboard

- **File:** `dashboard.html`
- **Overview:**  
  A comprehensive dashboard for monitoring and managing the application:
  
  - **Metrics Visualization:**
    - Interactive charts showing activity over time
    - Filterable by date range
    - Visual representation of success/failure rates
    - Summary statistics with calculated metrics
  
  - **Excel Upload Feature:**
    - Drag-and-drop file upload interface
    - Support for various Excel formats with column mapping
    - Visual feedback during upload process
    - Detailed success/error messages
    - Multiple UPC support with comma-separated values
  
  - **Database Information:**
    - Product count and last update time
    - Supported column formats documentation
    - Visual representation of database statistics
  
  - **Item-Level Events:**
    - Detailed table of individual lookup events
    - Filterable by date range
    - Loading indicators and empty state handling
  
  - **Failed Image Analysis:**
    - View of the latest failed barcode image
    - Timestamp and metadata display
    - Collapsible section for space efficiency

### Admin Login Page

- **File:** `admin_login.html`
- **Overview:**  
  A secure and visually appealing login interface:
  
  - **Branded Experience:**
    - Logo and application name prominently displayed
    - Consistent styling with main application
    - Background image that changes with theme
  
  - **Enhanced Security:**
    - Password field with icon and visual feedback
    - Improved error messages with icons
    - Clear login button with icon
  
  - **User Experience:**
    - Animated card with shadow effects
    - Link back to main application
    - Dark/light mode toggle
    - Responsive design for all device sizes

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

