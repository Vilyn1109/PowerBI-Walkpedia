'''Import images from Walkscape wiki activities page'''
import requests
from bs4 import BeautifulSoup
import pandas as pd

#def scrape_walkscape_activities():
url = "https://wiki.walkscape.app/wiki/Activities"
response = requests.get(url)

if response.status_code != 200:
    print(f"Failed to retrieve page. Status code: {response.status_code}")
    #return None

soup = BeautifulSoup(response.text, 'html.parser')

images_data = []

for img in soup.find_all('img'):
    img_src = img.get('src')
    
    # convert relative url if needed
    if img_src and img_src.startswith('/'):
        img_src = f"https://wiki.walkscape.app{img_src}"
  
    if img_src:
        images_data.append([img_src])

df = pd.DataFrame(images_data, columns=['image'])