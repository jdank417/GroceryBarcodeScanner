import os
import shutil
import requests

def download_and_replace_xlsx(download_url, final_xlsx="temp_download.xlsx"):
    temp_download_path = final_xlsx + ".download"

    response = requests.get(download_url, stream=True)
    if response.status_code == 200:
        with open(temp_download_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print("Temporary XLSX downloaded successfully.")

        # Remove the old file if it exists (avoid locking issues)
        if os.path.exists(final_xlsx):
            os.remove(final_xlsx)
            print(f"Removed old file: {final_xlsx}")

        # Move the temporary file to final path
        shutil.move(temp_download_path, final_xlsx)
        print(f"New file has replaced the old file: {final_xlsx}")
    else:
        print(f"Download failed. Status code: {response.status_code}")


if __name__ == "__main__":
    # Example direct-download link
    url = "https://mywentworth-my.sharepoint.com/:x:/g/personal/dankj_wit_edu/Ee3LabYq8OxMlr1-AYQ07gIBkIRg1orbQDpH0n82AMqu0g?download=1"
    download_and_replace_xlsx(url, "temp_download.xlsx")
