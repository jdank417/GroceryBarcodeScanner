from flask import Flask, render_template, request, redirect, url_for, flash
from PIL import Image
import pandas as pd
import os
from pyzbar.pyzbar import decode
import cv2
import numpy as np
import tensorflow as tf
from tensorflow.keras.preprocessing import image

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

# Load pretrained MobileNet model from Keras
model = tf.keras.applications.MobileNetV2(input_shape=(224, 224, 3), include_top=False, weights='imagenet')

# Freeze the base model layers to prevent training
model.trainable = False


def preprocess_image(img):
    # Resize the image to the input size of the model (224x224 for MobileNetV2)
    img_resized = cv2.resize(img, (224, 224))  # Adjust size based on your model's input
    img_array = image.img_to_array(img_resized)
    img_array = np.expand_dims(img_array, axis=0)  # Add batch dimension
    img_array /= 255.0  # Normalize image
    return img_array


def detect_barcode_with_cnn(img_path):
    img = cv2.imread(img_path)
    preprocessed_img = preprocess_image(img)

    # Make prediction using the pretrained MobileNet model
    prediction = model.predict(preprocessed_img)

    # Since MobileNet is a general-purpose model, this step is just for illustration
    # You can implement specific logic based on prediction (e.g., checking for barcode-like features)
    # Here, we decode the image using pyzbar if the model detects a barcode-like object
    barcodes = decode(img)

    if barcodes:
        return barcodes[0].data.decode("utf-8")  # Return the barcode data if detected
    else:
        return None


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

            # Use CNN (MobileNet) to detect barcode in the image
            barcode_data = detect_barcode_with_cnn(file_path)

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
