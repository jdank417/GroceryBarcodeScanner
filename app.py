import os
from functools import lru_cache

import cv2
import numpy as np
import pandas as pd
import requests
import tensorflow as tf
from flask import Flask, request, jsonify, send_from_directory
from pyzbar.pyzbar import decode
from tensorflow.keras.preprocessing import image

app = Flask(__name__, static_folder='frontend/build')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.secret_key = 'supersecretkey'

# Load Excel data
EXCEL_FILE_PATH = 'Item Database/Inventory.xlsx'
df = pd.read_excel(EXCEL_FILE_PATH)


@lru_cache(maxsize=100)
def lookup_item(barcode_data):
    barcode_data = str(barcode_data).strip()
    df["ItemNumber"] = df["ItemNumber"].astype(str).str.strip()
    item_info = df[df["ItemNumber"] == barcode_data]
    if not item_info.empty:
        item_name = item_info["ItemName"].values[0]
        item_price = item_info["ItemPrice"].values[0]
        return item_name, item_price
    else:
        return None, None


os.makedirs(os.path.join("static", "uploads"), exist_ok=True)

model = tf.keras.applications.MobileNetV2(input_shape=(224, 224, 3), include_top=False, weights='imagenet')
model.trainable = False


def resize_image(img, target_size=(800, 800)):
    return cv2.resize(img, target_size)


def preprocess_image(img):
    img_resized = cv2.resize(img, (224, 224))
    img_array = image.img_to_array(img_resized)
    img_array = np.expand_dims(img_array, axis=0)
    img_array /= 255.0
    return img_array


def detect_barcode_with_pyzbar_first(img_path):
    img = cv2.imread(img_path)
    resized_img = resize_image(img)
    barcodes = decode(resized_img)
    if barcodes:
        return barcodes[0].data.decode("utf-8")
    preprocessed_img = preprocess_image(img)
    prediction = model.predict(preprocessed_img)
    return None


def download_image_from_url(url, save_path):
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open(save_path, 'wb') as out_file:
            out_file.write(response.content)
        return True
    return False


@app.route("/upload", methods=["POST"])
def upload_image():
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    file_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
    file.save(file_path)
    barcode_data = detect_barcode_with_pyzbar_first(file_path)
    if barcode_data:
        item_name, item_price = lookup_item(barcode_data)
        os.remove(file_path)
        if item_name and item_price:
            return jsonify({"item_name": item_name, "item_price": item_price}), 200
        else:
            return jsonify({"error": "Item not found"}), 404
    else:
        os.remove(file_path)
        return jsonify({"error": "No barcode detected"}), 400


@app.route("/barcode", methods=["POST"])
def barcode_lookup():
    data = request.get_json()
    barcode_id = data.get("barcode_id")
    if barcode_id:
        item_name, item_price = lookup_item(barcode_id)
        if item_name and item_price:
            return jsonify({"item_name": item_name, "item_price": item_price}), 200
        else:
            return jsonify({"error": "Item not found"}), 404
    else:
        return jsonify({"error": "Please enter a barcode ID"}), 400


@app.route("/url", methods=["POST"])
def url_upload():
    data = request.get_json()
    url = data.get("url")
    if url:
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], "downloaded_image.jpg")
        if download_image_from_url(url, file_path):
            barcode_data = detect_barcode_with_pyzbar_first(file_path)
            if barcode_data:
                item_name, item_price = lookup_item(barcode_data)
                os.remove(file_path)
                if item_name and item_price:
                    return jsonify({"item_name": item_name, "item_price": item_price}), 200
                else:
                    return jsonify({"error": "Item not found"}), 404
            else:
                os.remove(file_path)
                return jsonify({"error": "No barcode detected"}), 400
        else:
            return jsonify({"error": "Failed to download image from URL"}), 400
    else:
        return jsonify({"error": "No URL provided"}), 400


@app.route("/", defaults={'path': ''})
@app.route("/<path:path>")
def serve(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')


if __name__ == "__main__":
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(host="0.0.0.0", port=44456, debug=True)
