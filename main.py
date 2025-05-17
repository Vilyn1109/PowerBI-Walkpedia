import requests
from bs4 import BeautifulSoup
import pandas as pd

def scrape_walkscape_activities():
    url = "https://wiki.walkscape.app/wiki/Activities"
    response = requests.get(url)

    if response.status_code != 200:
        print(f"Failed to retrieve page. Status code: {response.status_code}")
        return None

    soup = BeautifulSoup(response.text, 'html.parser')

    # Find all tables in the page
    tables = soup.find_all('table', class_='wikitable')
    
    all_tables_data = []
    
    # Process each table
    for i, table in enumerate(tables):
        # Extract headers
        headers = []
        header_row = table.find('tr')
        if header_row:
            headers = [th.text.strip() for th in header_row.find_all(['th'])]
        
        # Skip tables with no headers
        if not headers:
            continue
        
        # Extract rows
        rows = []
        for row in table.find_all('tr')[1:]:  # Skip header row
            cells = [td.text.strip() for td in row.find_all(['td'])]
            if cells:
                rows.append(cells)
        
        # Create DataFrame
        if rows:
            df = pd.DataFrame(rows, columns=headers)
            all_tables_data.append({
                'table_number': i+1,
                'data': df
            })
    
    return all_tables_data

def save_tables_to_csv(tables_data):
    if not tables_data:
        print("No tables found or could not be processed.")
        return
    
    for table in tables_data:
        table_num = table['table_number']
        df = table['data']
        filename = f"walkscape_activities_table_{table_num}.csv"
        df.to_csv(filename, index=False)
        print(f"Saved table {table_num} to {filename}")

# Main execution
if __name__ == "__main__":
    print("Scraping Walkscape Activities wiki...")
    tables_data = scrape_walkscape_activities()
    
    if tables_data:
        print(f"Found {len(tables_data)} tables.")
        
        # Save tables to CSV files
        save_to_csv = input("\nDo you want to save these tables as CSV files? (y/n): ")
        if save_to_csv.lower() == 'y':
            save_tables_to_csv(tables_data)
    else:
        print("No tables were successfully extracted.")