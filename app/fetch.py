import requests
import os

os.makedirs("data/raw", exist_ok=True)

urls = [
    "https://www.rbi.org.in/scripts/BS_PressReleaseDisplay.aspx?prid=53372",
    "https://rbidocs.rbi.org.in/rdocs/content/pdfs/BEAWARE07032022.pdf",
    "https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx?prid=53185"
]

names = [
    "rbi_press_release.html",
    "beaware.pdf",
    "consumer_awareness.html"
]

for i in range(len(urls)):

    try:
        response = requests.get(urls[i], timeout=30)

        response.raise_for_status()

        file = open("data/raw/" + names[i], "wb")
        file.write(response.content)
        file.close()

        print(names[i], "downloaded successfully")

    except requests.exceptions.RequestException as error:
        print("Download failed:", error)