'''Simplified WalkScape Wiki scraper for Power BI compatibility. Only processes tables with images.'''
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from urllib.parse import urljoin
import re

class WalkScapeActivityScraper:
    def __init__(self, base_url="https://wiki.walkscape.app"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Initialize dataframes
        self.activity_info_df = pd.DataFrame()
        self.experience_info_df = pd.DataFrame()
        self.drops_df = pd.DataFrame()
        self.special_drops_df = pd.DataFrame()
    
    def get_page(self, url):
        """Fetch a web page with error handling and rate limiting"""
        try:
            time.sleep(0.5)
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except requests.RequestException as e:
            print(f"Error fetching {url}: {e}")
            return None
    
    def extract_activity_links(self, activities_url):
        """Extract activity links from the main activities page"""
        soup = self.get_page(activities_url)
        if not soup:
            return []
        
        activity_links = []
        tables = soup.find_all('table')
        
        # Find table containing 'Antique Market Assessor'
        target_table = None
        for table in tables:
            if 'antique market assessor' in table.get_text().lower():
                target_table = table
                break
        
        if not target_table:
            print("Could not find activities table")
            return []
        
        # Extract links from second column of each row
        rows = target_table.find_all('tr')
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 2:
                links = cells[1].find_all('a')
                for link in links:
                    href = link.get('href')
                    if href and '/wiki/' in href:
                        activity_name = link.get_text(strip=True)
                        if activity_name and len(activity_name) > 2:
                            activity_url = urljoin(self.base_url, href)
                            activity_links.append({
                                'name': activity_name,
                                'url': activity_url
                            })
        
        # Remove duplicates
        unique_links = []
        seen_urls = set()
        for link in activity_links:
            if link['url'] not in seen_urls:
                seen_urls.add(link['url'])
                unique_links.append(link)
        
        print(f"Found {len(unique_links)} unique activities")
        return unique_links
    
    def has_images(self, table):
        """Check if table contains images"""
        return bool(table.find_all('img'))
    
    def has_max_efficiency(self, table):
        """Check if table contains 'Max Efficiency:' in any row"""
        for row in table.find_all('tr'):
            row_text = row.get_text()
            if 'Max Efficiency:' in row_text:
                return True
        return False
    
    def get_table_type(self, headers, table):
        """Determine table type based on column headers and content"""
        # First check for Max Efficiency - this takes priority
        if self.has_max_efficiency(table):
            return 'activity_info'
        
        header_text = ' '.join(headers).lower()
        
        if 'skill(s)' in header_text and 'baseexp' in header_text:
            return 'experience_info'
        elif 'type' in header_text:
            return 'special_drops'
        elif 'item' in header_text and 'quantity' in header_text:
            return 'drops'
        else:
            return None
    
    def clean_table_data(self, table):
        """Convert HTML table to list of dictionaries"""
        rows = table.find_all('tr')
        if len(rows) < 1:
            return []
        
        # Extract headers
        header_row = rows[0]
        header_cells = header_row.find_all(['th', 'td'])
        headers = [cell.get_text(strip=True) for cell in header_cells if cell.get_text(strip=True)]
        
        if not headers:
            return []
        
        # Extract data rows
        data = []
        for row in rows[1:]:
            cells = row.find_all(['td', 'th'])
            if not cells:
                continue
            
            row_data = {}
            cell_index = 0
            
            # Skip row number if first cell is just a number
            if cells and cells[0].get_text(strip=True).isdigit():
                cell_index = 1
            
            # Process each header
            for header_idx, header in enumerate(headers):
                if cell_index >= len(cells):
                    row_data[header] = ""
                    continue
                
                # Handle columns with images - both Item columns and Skill(s) columns
                if 'item' in header.lower() or 'skill(s)' in header.lower():
                    current_cell_text = cells[cell_index].get_text(strip=True)
                    
                    # If current cell is empty/short (likely image), use next cell
                    if (not current_cell_text or len(current_cell_text) <= 2) and cell_index + 1 < len(cells):
                        cell_index += 1
                        if cell_index < len(cells):
                            item_text = self.extract_item_name(cells[cell_index])
                            row_data[header] = item_text
                        else:
                            row_data[header] = ""
                    else:
                        row_data[header] = self.extract_item_name(cells[cell_index])
                else:
                    # Regular column processing
                    if cell_index < len(cells):
                        cell_text = cells[cell_index].get_text(strip=True)
                        cell_text = re.sub(r'\[\d+\]', '', cell_text)  # Remove reference numbers
                        cell_text = re.sub(r'\s+', ' ', cell_text).strip()
                        row_data[header] = cell_text
                    else:
                        row_data[header] = ""
                
                cell_index += 1
            
            # Only add row if it has meaningful data
            if any(value and str(value).strip() for value in row_data.values()):
                data.append(row_data)
        
        return data
    
    def extract_item_name(self, cell):
        """Extract item name from a cell"""
        # Try to get text from links first
        links = cell.find_all('a')
        if links:
            for link in links:
                link_text = link.get_text(strip=True)
                if link_text and len(link_text) > 1:
                    return re.sub(r'\[\d+\]', '', link_text).strip()
        
        # If no good link text, get all text from cell
        item_text = cell.get_text(strip=True)
        return re.sub(r'\[\d+\]', '', item_text).strip()
    
    def extract_tables_from_activity_page(self, activity_name, activity_url):
        """Extract tables from an activity page"""
        soup = self.get_page(activity_url)
        if not soup:
            return
        
        print(f"Processing activity: {activity_name}")
        
        tables = soup.find_all('table')
        tables_processed = 0
        
        for i, table in enumerate(tables):
            # Only process tables with images
            if not self.has_images(table):
                continue
            
            table_data = self.clean_table_data(table)
            if not table_data:
                continue
            
            headers = list(table_data[0].keys())
            table_type = self.get_table_type(headers, table)
            
            if not table_type:
                continue
            
            print(f"  Found {table_type} table with {len(table_data)} rows")
            
            # Add activity name to each row
            for row in table_data:
                row['Activity'] = activity_name
            
            # Append to appropriate dataframe
            temp_df = pd.DataFrame(table_data)
            if table_type == 'activity_info':
                self.activity_info_df = pd.concat([self.activity_info_df, temp_df], ignore_index=True)
            elif table_type == 'experience_info':
                self.experience_info_df = pd.concat([self.experience_info_df, temp_df], ignore_index=True)
            elif table_type == 'drops':
                self.drops_df = pd.concat([self.drops_df, temp_df], ignore_index=True)
            elif table_type == 'special_drops':
                self.special_drops_df = pd.concat([self.special_drops_df, temp_df], ignore_index=True)
            
            tables_processed += 1
        
        print(f"  Processed {tables_processed} tables")
    
    def scrape_all_activities(self, activities_url):
        """Main method to scrape all activities"""
        print("Extracting activity links...")
        activity_links = self.extract_activity_links(activities_url)
        
        if not activity_links:
            print("No activity links found!")
            return
        
        for i, activity in enumerate(activity_links, 1):
            print(f"\nProcessing {i}/{len(activity_links)}: {activity['name']}")
            self.extract_tables_from_activity_page(activity['name'], activity['url'])
        
        print("Scraping completed!")
    
    def print_summary(self):
        """Print summary of scraped data"""
        print("\n=== SCRAPING SUMMARY ===")
        print(f"Activity Info records: {len(self.activity_info_df)}")
        print(f"Experience Info records: {len(self.experience_info_df)}")
        print(f"Drops records: {len(self.drops_df)}")
        print(f"Special Drops records: {len(self.special_drops_df)}")
        
        # Show sample data
        for name, df in [
            ('Activity Info', self.activity_info_df),
            ('Experience Info', self.experience_info_df),
            ('Drops', self.drops_df),
            ('Special Drops', self.special_drops_df)
        ]:
            if not df.empty:
                print(f"\nSample {name} data:")
                print(df.head(2))

# Initialize and run scraper
scraper = WalkScapeActivityScraper()
activities_url = "https://wiki.walkscape.app/wiki/Activities"

try:
    scraper.scrape_all_activities(activities_url)
    scraper.print_summary()
    
    # Make dataframes available for Power BI
    activity_info = scraper.activity_info_df
    experience_info = scraper.experience_info_df
    drops = scraper.drops_df
    special_drops = scraper.special_drops_df
    
    available_dataframes = []
    if not activity_info.empty:
        available_dataframes.append('activity_info')
    if not experience_info.empty:
        available_dataframes.append('experience_info')
    if not drops.empty:
        available_dataframes.append('drops')
    if not special_drops.empty:
        available_dataframes.append('special_drops')
    
    print(f"\nDataframes available for Power BI: {available_dataframes}")
    
except Exception as e:
    print(f"An error occurred: {e}")
    import traceback
    traceback.print_exc()
    
    # Create empty dataframes as fallback
    activity_info = pd.DataFrame()
    experience_info = pd.DataFrame()
    drops = pd.DataFrame()
    special_drops = pd.DataFrame()