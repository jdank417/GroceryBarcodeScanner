# Barcode Scanner Web App

This project is a web-based barcode scanner that allows users to upload an image of a barcode using their phone’s camera. The app decodes the barcode and retrieves relevant item information (name and price) from an Excel file.

## Features

- **Mobile-Friendly**: Users can access the web app via their mobile device, enabling them to scan barcodes directly from their phone.
- **Excel Data Integration**: The app searches an Excel file to match barcode data with item information, including the item’s name and price.
- **Real-Time Feedback**: Displays the scanned item’s details or provides a message if the item is not found.

## Requirements

Ensure you have the following installed:

- Python 3.7+
- Required Python packages:
  - Flask
  - Pyzbar
  - Pillow
  - Pandas
  - Openpyxl (for Excel file handling)
