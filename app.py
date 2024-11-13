from flask import Flask, render_template, request, redirect, url_for, flash
from pyzbar.pyzbar import decode
from PIL import Image
import pandas as pd
import os

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


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # Check if the post request has the file part
        if "file" not in request.files:
            flash("No file part")
            return redirect(request.url)

        file = request.files["file"]
        if file.filename == "":
            flash("No selected file")
            return redirect(request.url)

        if file:
            # Save the file to the upload folder
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
            file.save(file_path)

            # Decode the barcode from the image
            image = Image.open(file_path)
            barcodes = decode(image)
            if barcodes:
                barcode_data = barcodes[0].data.decode("utf-8")

                # Look up item in the Excel file
                item_name, item_price = lookup_item(barcode_data)

                if item_name and item_price:
                    flash(f"Item: {item_name}, Price: ${item_price}")
                else:
                    flash("Item not found in the Excel file")
            else:
                flash("No barcode detected in the image.")

            # Remove the file after processing
            os.remove(file_path)

    return render_template("index.html")


if __name__ == "__main__":
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(host="0.0.0.0", port=8000, debug=True)
