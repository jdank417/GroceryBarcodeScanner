from pyzbar.pyzbar import decode
import cv2


def test_barcode_detection(image_path):
    # Load an image with a barcode
    image = cv2.imread(image_path)
    barcodes = decode(image)

    if barcodes:
        for barcode in barcodes:
            print("Detected barcode data:", barcode.data.decode("utf-8"))
    else:
        print("No barcode detected in the image.")


# Replace 'path_to_test_image.jpg' with an image containing a barcode
test_barcode_detection('testBarcode.jpg')
