from flask import Flask, render_template, request, redirect, url_for, flash
from PIL import Image
import pandas as pd
import os
from pyzbar.pyzbar import decode
import cv2
import numpy as np

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.secret_key = 'supersecretkey'

# Load Excel data
EXCEL_FILE_PATH = 'Inventory.xlsx'  # Update with your actual file path
df = pd.read_excel(EXCEL_FILE_PATH)

def lookup_item(barcode_data):
    barcode_data = str(barcode_data).strip()
    df["ItemNumber"] = df["ItemNumber"].astype(str).str.strip()

    # Search for the item in the Excel sheet
    item_info = df[df["ItemNumber"] == barcode_data]

    if not item_info.empty:
        # Extract item name and price
        item_name = item_info["ItemName"].values[0]
        item_price = item_info["ItemPrice"].values[0]
        return item_name, item_price
    else:
        return None, None

# Ensure the static/uploads folder exists
os.makedirs(os.path.join("static", "uploads"), exist_ok=True)

@app.route("/", methods=["GET", "POST"])
def index():
    processed_image_path = None  # Initialize variable for processed image path

    if request.method == "POST":
        if "file" not in request.files:
            flash("No file part")
            return redirect(request.url)

        file = request.files["file"]
        if file.filename == "":
            flash("No selected file")
            return redirect(request.url)

        if file:
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
            file.save(file_path)

            # Open the image and preprocess
            image = Image.open(file_path)
            image = image.convert("L")  # Convert the image to grayscale
            cv_image = np.array(image)

            # Apply adaptive thresholding to preserve the barcode
            binary_image = cv2.adaptiveThreshold(
                cv_image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )
            resized_image = cv2.resize(binary_image, (binary_image.shape[1] * 2, binary_image.shape[0] * 2))

            # Save the processed image in the static/uploads folder for display
            processed_image_filename = "processed_" + file.filename
            processed_image_path = os.path.join("static", "uploads", processed_image_filename)
            cv2.imwrite(processed_image_path, resized_image)

            # Decode the barcode from the preprocessed image
            barcodes = decode(Image.fromarray(resized_image))
            if barcodes:
                barcode_data = barcodes[0].data.decode("utf-8")
                item_name, item_price = lookup_item(barcode_data)

                if item_name and item_price:
                    flash(f"Item: {item_name}, Price: ${item_price}")
                else:
                    flash("Item not found in the Excel file")
            else:
                flash("No barcode detected in the image.")

            os.remove(file_path)  # Remove original uploaded file

    return render_template("index.html", processed_image_path=processed_image_path)

if __name__ == "__main__":
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(host="0.0.0.0", port=8000, debug=True)