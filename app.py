from flask import Flask, render_template, request, flash
import pandas as pd
import os
from functools import lru_cache

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Path to your Excel file
EXCEL_FILE_PATH = 'Item Database/output.xlsx'

# Read the Excel file and force "ItemNumber" to be read as a string
df = pd.read_excel(EXCEL_FILE_PATH, dtype={'ItemNumber': str})

# Clean the "ItemNumber" column: remove any trailing '.0' and extra spaces
df["ItemNumber"] = (
    df["ItemNumber"]
    .str.replace(r'\.0$', '', regex=True)
    .str.strip()
)


@lru_cache(maxsize=100)
def lookup_item(barcode_data):
    """
    Look up item name and price in the Excel dataframe based on the SKU.
    Returns (item_name, item_price) or (None, None) if not found!
    """
    barcode_data = str(barcode_data).strip()
    print(f"Looking up barcode: '{barcode_data}'")  # Debug print

    # Filter the dataframe
    item_info = df[df["ItemNumber"] == barcode_data]
    if not item_info.empty:
        item_name = item_info["ItemName"].values[0]
        item_price = item_info["ItemPrice"].values[0]
        return item_name, item_price
    else:
        return None, None


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        barcode_id = request.form.get("barcode_id")
        if barcode_id:
            item_name, item_price = lookup_item(barcode_id)
            if item_name and item_price:
                flash(f"Item: {item_name}, Price: ${item_price}")
            else:
                flash("Item not found in the Excel file.")
        else:
            flash("Please enter a valid SKU (barcode).")
    return render_template("index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
