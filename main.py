import cv2
import pandas as pd
from pyzbar.pyzbar import decode


def decode_barcode(image_path):
    # Load the image
    image = cv2.imread(image_path)

    # Decode the barcode
    barcodes = decode(image)

    if barcodes:
        # Return the decoded data from the first barcode found
        barcode_data = barcodes[0].data.decode("utf-8")
        return barcode_data
    else:
        return None


def lookup_item(barcode_data, excel_file_path):
    # Load the Excel file
    df = pd.read_excel(excel_file_path)

    # Check if the column names match our requirements
    if not all(col in df.columns for col in ["ItemNumber", "ItemName", "ItemPrice"]):
        raise ValueError("Excel file must contain columns: 'ItemNumber', 'ItemName', 'ItemPrice'")

    # Convert both barcode_data and the ItemNumber column to strings for comparison
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


# Main function to run the process
def main(image_path, excel_file_path):
    # Step 1: Decode the barcode from the image
    item_number = decode_barcode(image_path)

    if item_number:
        # Step 2: Lookup the item in the Excel file
        item_name, item_price = lookup_item(item_number, excel_file_path)

        if item_name and item_price:
            print(f"Item Number: {item_number}")
            print(f"Item Name: {item_name}")
            print(f"Item Price: {item_price}")
        else:
            print("Item not found in the Excel file.")
    else:
        print("No barcode detected in the image.")


# Example usage
image_path = '62345678.png'
excel_file_path = 'Inventory.xlsx'
main(image_path, excel_file_path)
