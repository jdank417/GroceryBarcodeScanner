from flask import Flask, render_template, request, redirect, url_for, flash
from PIL import Image
import pandas as pd
import os
from pyzbar.pyzbar import decode
import cv2
import numpy as np
import tensorflow as tf
from tensorflow.keras.preprocessing import image
from functools import lru_cache

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.secret_key = 'supersecretkey'

# Load Excel data
EXCEL_FILE_PATH = 'Item Database/Inventory.xlsx'  # Update with your actual file path
df = pd.read_excel(EXCEL_FILE_PATH)


# Caching for frequent barcode lookups
@lru_cache(maxsize=100)
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
os.makedirs(os.path.join("../static", "uploads"), exist_ok=True)

# Load pretrained MobileNet model from Keras and convert to TensorFlow Lite model
model = tf.keras.applications.MobileNetV2(input_shape=(224, 224, 3), include_top=False, weights='imagenet')
model.trainable = False


def resize_image(img, target_size=(800, 800)):
    # Resize the image to reduce processing load
    return cv2.resize(img, target_size)


def preprocess_image(img):
    # Resize the image to the input size of the model (224x224 for MobileNetV2)
    img_resized = cv2.resize(img, (224, 224))
    img_array = image.img_to_array(img_resized)
    img_array = np.expand_dims(img_array, axis=0)  # Add batch dimension
    img_array /= 255.0  # Normalize image
    return img_array


def detect_barcode_with_pyzbar_first(img_path):
    img = cv2.imread(img_path)
    resized_img = resize_image(img)

    # Try decoding with pyzbar on resized image
    barcodes = decode(resized_img)
    if barcodes:
        return barcodes[0].data.decode("utf-8")  # Return the barcode data if detected

    # Fall back to CNN detection if pyzbar fails
    preprocessed_img = preprocess_image(img)
    prediction = model.predict(preprocessed_img)

    # Add specific logic here if CNN needs to make a decision
    return None  # or return the barcode if detected by the CNN


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

            # Use Pyzbar first, then CNN to detect barcode in the image
            barcode_data = detect_barcode_with_pyzbar_first(file_path)

            if barcode_data:
                # Decode the barcode data
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
