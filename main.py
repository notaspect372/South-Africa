from bs4 import BeautifulSoup
import requests
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import time
import re
import math
import os  # Import os to handle file paths and directories

# Function to clean unwanted characters from text fields
def clean_text(text):
    if text:
        return text.replace(u'\xa0', ' ').replace("''", "'").strip()
    return None

# Function to clean dictionary values
def clean_dict(data_dict):
    if isinstance(data_dict, dict):
        return {clean_text(key): clean_text(value) for key, value in data_dict.items()}
    return data_dict

# Geocoding function to get latitude and longitude
def get_lat_long(address):
    try:
        geolocator = Nominatim(user_agent="my_geopy_app")
        location = geolocator.geocode(address, timeout=10)
        if location:
            return location.latitude, location.longitude
        else:
            return None, None
    except GeocoderTimedOut:
        return None, None

def get_total_pages(base_url):
    response = requests.get(base_url)
    soup = BeautifulSoup(response.content, 'html.parser')

    # Locate the total listings count
    total_listings_element = soup.select_one('.listing-results-layout__desktop-item-count')
    if total_listings_element:
        total_listings_text = total_listings_element.get_text(strip=True).replace("\xa0", "")  # Remove non-breaking spaces
        
        # Use regex to extract only the numeric value (e.g., "1150")
        match = re.search(r'of\s*([\d,]+)', total_listings_text)
        if match:
            total_listings = int(match.group(1).replace(',', ''))  # Remove commas and convert to int
            
            total_pages = (total_listings + 19) // 20  # Rounding up for full pages
            print(f"Total listings: {total_listings}, Total pages: {total_pages}")
            return total_pages
        else:
            print("Could not extract total listings number.")
            return 0
    else:
        print("Could not find total listings on the page.")
        return 0

# Function to scrape all property URLs from a given base URL
def scrape_property_urls(base_url):
    total_pages = get_total_pages(base_url)  # Fetch total pages
    property_urls = []

    for page_number in range(1, total_pages + 1):
        url = base_url + "?page=" + str(page_number)
        print(f"Scraping page: {page_number} - {url}")

        try:
            response = requests.get(url)
            soup = BeautifulSoup(response.content, 'html.parser')

            # Try first selector
            links = soup.find_all('a', class_='development-result-card-link', href=True)

            # If no URLs found, try alternative selector
            if not links:
                print("First selector not found, trying alternative selector...")
                links = soup.find_all('a', class_='listing-result', href=True)

            # Extract and store property URLs
            for link in links:
                href = link['href']
                full_url = "https://www.privateproperty.co.za" + href
                property_urls.append(full_url)

        except Exception as e:
            print(f"Error scraping page {page_number}: {e}")

    return property_urls

def scrape_property_details(soup):
    property_details = {}
    details_section = soup.find('div', class_='property-details')
    
    if details_section:
        items = details_section.find_all('li', class_='property-details__list-item')
        
        for item in items:
            label_element = item.find('span', class_='property-details__name-value')
            value_element = item.find('span', class_='property-details__value')
            
            if label_element and value_element:
                label = clean_text(label_element.get_text().replace(value_element.get_text(), '').strip())
                value = clean_text(value_element.get_text(strip=True))
                property_details[label] = value
    
    return clean_dict(property_details)

# Function to scrape data from each property page
def scrape_property_data(property_url):
    response = requests.get(property_url)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    name = clean_text(soup.find('h1', class_='listing-details__title').get_text(strip=True)) if soup.find('h1', class_='listing-details__title') else None
    
    address = clean_text(soup.find('div', class_='listing-details__address').get_text(strip=True)) if soup.find('div', class_='listing-details__address') else None

    description = None
    desc_section = soup.find('div', class_='listing-description__text')
    if desc_section:
        description = clean_text(desc_section.get_text(strip=True))
    else:
        desc_alt_section = soup.find('div', class_='listing-description-wrapper')
        if desc_alt_section:
            description = clean_text(" ".join(p.get_text(strip=True) for p in desc_alt_section.find_all('p')))
    
    # Try different sources for price
    price = None
    price_section = soup.find('div', class_='listing-price-display__price')
    if price_section:
        price = clean_text(price_section.get_text(strip=True))
    else:
        price_alt_section = soup.find('p', class_='listing-price-display__price')
        if price_alt_section:
            price = clean_text(price_alt_section.get_text(strip=True))
    
    characteristics = {}
    characteristics_section = soup.find('div', class_='property-features')
    if characteristics_section:
        for item in characteristics_section.find_all('li', class_='property-features__list-item'):
            key_value = item.find('span', class_='property-features__name-value')
            if key_value:
                key = clean_text(key_value.contents[0])
                value = clean_text(key_value.find('span', class_='property-features__value').get_text(strip=True)) if key_value.find('span', 'property-features__value') else None
                characteristics[key] = value

    characteristics = clean_dict(characteristics)

    property_details = scrape_property_details(soup)
    
    # Determine transaction type
    if "sale" in property_url.lower():
        transaction_type = "Sales"
    else:
        transaction_type = "Rentals"

    # Extract sub-address (first part of the full address)
    if address:
        sub_address = address.split(',')[0]
        latitude, longitude = get_lat_long(sub_address)
    else:
        sub_address = "N/A"
        latitude, longitude = None, None

    # Create a dictionary with the cleaned data
    data = {
        "URL": property_url,
        "Name": name,
        "Description": description,
        "Address": address,
        "Latitude": latitude,
        "Longitude": longitude,
        "Area": property_details.get("Land size", "N/A"),
        'Property Type': property_details.get("Property type", "N/A"),
        "Transaction Type": transaction_type,
        "Price": price,
        "Characteristics": characteristics,
        "Property Details": property_details,
    }
    
    return data

# Function to save data to Excel in the output directory
def save_to_excel(data, base_url):
    # Replace invalid characters in file name
    file_name = base_url.replace("https://", "").replace("/", "_").replace("?", "_").replace(":", "_") + ".xlsx"
    
    # Create the output directory if it doesn't exist
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    
    # Save the Excel file in the output directory
    file_path = os.path.join(output_dir, file_name)
    df = pd.DataFrame(data)
    df.to_excel(file_path, index=False)
    print(f"Data saved to {file_path}")

# Main function to scrape multiple base URLs
def scrape_multiple_urls(base_urls):
    for base_url in base_urls:
        print(f"Scraping data from: {base_url}")
        
        property_urls = scrape_property_urls(base_url)
        print(f"Found {len(property_urls)} property URLs")
        
        all_data = []
        for property_url in property_urls:
            property_data = scrape_property_data(property_url)
            print(property_data)
            all_data.append(property_data)
        
        save_to_excel(all_data, base_url)

# Example usage
base_urls = [
    "https://www.privateproperty.co.za/for-sale/gauteng/centurion/32"
]

scrape_multiple_urls(base_urls)
