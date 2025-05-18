'''For importing locations from the walkscape wiki'''
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

url_Regions = "https://wiki.walkscape.app/wiki/Arenum#Regions"

response = requests.get(url_Regions)

if response.status_code != 200:
    print(f"Failed to retrieve page. Status code: {response.status_code}")
    #return None

soup = BeautifulSoup(response.text, 'html.parser')

# Find regions header
regions_header = None
for header in soup.find_all(['h1', 'h2', 'h3', 'h4']):
    if header.get_text().strip() == "Regions":
        regions_header = header
        break

header_tag = regions_header.name
header_level = int(header_tag[1])

 # Find all links under the Regions section until the next header of same or higher level
regions_links = []
current = regions_header.next_element

while current:
    # Check if we've reached the next header of same or higher level
    if current.name and current.name[0] == 'h' and int(current.name[1]) <= header_level:
        if current != regions_header:  # Make sure it's not the same header we started with
            break
            
    # If we find a link, add it to our list
    if current.name == 'a' and current.has_attr('href'):
        href = current['href']
        if href.startswith('/'):
            href = f"https://wiki.walkscape.app{href}"
        
        # Store both text and fixed URL
        regions_links.append({
            'name': current.get_text(),
            'url': href
        })

    # Move to the next element
    try:
        current = current.next_element
    except:
        break

df_links = pd.DataFrame(regions_links)
df_links.columns = ['region', 'link']

remove_items = \
    ['Coat_of_Arms.svg', 'Category:', 'Farming', 'Activities', 'Woodcutting', 'Fishing', 'Mining', 'Crafting', 'Gems', 'Walkscape', 'WalkScape', 'index']

for item in remove_items:
    df_links = df_links[~df_links['link'].str.contains(item)]

df_links = df_links.drop_duplicates(subset=['link'], keep='first')

# # # # #

# Visit each region page and extract locations

all_locations = []

for index, row in df_links.iterrows():
    link = row['link']
    region_name = row['region']

    time.sleep(1)

    response = requests.get(link)
    if response.status_code != 200:
        print(f"Failed to retrieve {link}. Status code: {response.status_code}")
        continue
        
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find Locations header
    locations_header = None
    for header in soup.find_all(['h1', 'h2', 'h3', 'h4']):
        if header.get_text().strip() == "Locations":
            locations_header = header
            break
    
    if not locations_header:
        print(f"No Locations header found in {region_name}")
        continue
    
    header_tag = locations_header.name
    header_level = int(header_tag[1])
    
    # Find the next list after the Locations header
    current = locations_header
    location_list = []
    
    # Look for lists (ul or ol) that follow the Locations header
    while current:
        current = current.find_next()
        if not current:
            break
            
        # Check if we've reached the next header of same or higher level
        if current.name and current.name[0] == 'h' and int(current.name[1]) <= header_level:
            break
            
        # Look for list items
        if current.name in ['ul', 'ol']:
            for li in current.find_all('li', recursive=True):
                location_text = li.get_text().strip()
                if location_text:
                    location_list.append({
                        'region': region_name,
                        'location': location_text
                    })
    
    if location_list:
        all_locations.extend(location_list)
        # print(f"Found {len(location_list)} locations in {region_name}")
    else:
        print(f"No locations found in {region_name}")

# Create final dataframe
df_locations = pd.DataFrame(all_locations)
df_locations = df_locations.drop_duplicates(subset=['location'], keep='first')