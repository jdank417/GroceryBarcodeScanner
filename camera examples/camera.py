import cv2
import os
import tkinter as tk
from tkinter import Button, Label
from PIL import Image, ImageTk

def capture_image(frame):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(script_dir, 'captured_image.jpg')
    cv2.imwrite(image_path, frame)
    print(f"Image saved at {image_path}")

def camera_app():
    # Initialize the camera
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("Error: Could not open camera.")
        return

    def show_frame():
        ret, frame = cap.read()
        if ret:
            # Convert the frame to an image that can be displayed in tkinter
            cv2image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(cv2image)
            imgtk = ImageTk.PhotoImage(image=img)
            lmain.imgtk = imgtk
            lmain.configure(image=imgtk)
        lmain.after(10, show_frame)

    def on_capture():
        ret, frame = cap.read()
        if ret:
            capture_image(frame)

    root = tk.Tk()
    root.title("Camera App")

    lmain = Label(root)
    lmain.pack()

    capture_button = Button(root, text="Capture", command=on_capture)
    capture_button.pack()

    show_frame()
    root.mainloop()

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    camera_app()