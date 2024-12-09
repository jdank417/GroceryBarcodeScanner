import pandas as pd

#Function straight from Backend/main.py
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

def main(excel_file_path):

    item_number = 22345678
    excel_file_path = '../Item Database/Inventory.xlsx'

    item_name, item_price = lookup_item(item_number, excel_file_path)

    print(f"Item Number: {item_number}")
    print(f"Item Name: {item_name}")
    print(f"Item Price: {item_price}")

main('../Item Database/Inventory.xlsx')