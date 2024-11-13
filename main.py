import cv2
import pandas as pd
from pyzbar.pyzbar import decode


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


def scan_barcode_from_camera(excel_file_path):
    # Initialize the camera
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)  # Set width to 1920px
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)  # Set height to 1080px

    print("Starting camera. Press 'q' to exit.")

    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            # Decode barcodes in the frame
            barcodes = decode(frame)
            for barcode in barcodes:
                # Extract the bounding box and draw a rectangle around it
                (x, y, w, h) = barcode.rect
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

                # Decode the barcode data
                barcode_data = barcode.data.decode("utf-8")
                barcode_type = barcode.type

                # Lookup item in Excel
                item_name, item_price = lookup_item(barcode_data, excel_file_path)

                if item_name and item_price:
                    text = f"Item: {item_name}, Price: ${item_price}"
                else:
                    text = "Item not found in the Excel file"

                # Display the decoded barcode data on the frame
                cv2.putText(frame, f"{barcode_type} - {barcode_data}", (x, y - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                cv2.putText(frame, text, (x, y + h + 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)

            # Display the frame with annotations
            cv2.imshow("Barcode Scanner", frame)

            # Press 'q' to exit the loop
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    except KeyboardInterrupt:
        print("\nExiting program due to Keyboard Interrupt.")
    finally:
        # Release the camera and close any open windows
        cap.release()
        cv2.destroyAllWindows()


# Run the camera-based barcode scanner
excel_file_path = 'Inventory.xlsx'
scan_barcode_from_camera(excel_file_path)
