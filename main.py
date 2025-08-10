import re
import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import time
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()
# Gmail credentials from .env file
GMAIL_USER = os.getenv('GMAIL_USER')
GMAIL_PASS = os.getenv('GMAIL_PASS')
EMAIL_RECIPIENTS = os.getenv('EMAIL_RECIPIENTS').split(',')
# Constants
BASE_URL = 'https://trouverunlogement.lescrous.fr'
URL = 'https://trouverunlogement.lescrous.fr/tools/41/search?bounds=5.2286902_43.3910329_5.5324758_43.1696205&'   #marseille
#URL = 'https://trouverunlogement.lescrous.fr/tools/41/search?'
CHECK_INTERVAL = 30 # Check every 30 secs


# Previous state
prev_accommodations = set()  # Using a set for unique IDs


def fetch_accommodations():
    """Fetches accommodation details from the listing pages."""
    accommodations = {}

    # Step 1: Get the total number of pages
    response = requests.get(URL, timeout=10)
    if response.status_code != 200:
        print(f"Failed to retrieve data: {response.status_code}")
        return accommodations

    soup = BeautifulSoup(response.content, 'html.parser')

    # Assuming the input field is unique, retrieve the max page value
    max_page_input = soup.find('input', {'type': 'number', 'title': 'Page à atteindre'})

    if max_page_input:
        max_pages = int(max_page_input['max'])
        print(f"Total pages found: {max_pages}")
    else:
        print("Failed to find the max page input.")
        return accommodations

    # Step 2: Loop through all pages
    for page in range(1, max_pages + 1):
        try:
            # Fetch the page content
            response = requests.get(URL + "page=" + str(page), timeout=10)
            if response.status_code != 200:
                print(f"Failed to retrieve page {page}: {response.status_code}")
                continue

            # Parse the page content using BeautifulSoup
            soup = BeautifulSoup(response.content, 'html.parser')

            # Find all <li> elements that match the class pattern
            accommodation_items = soup.find_all('li', class_=re.compile(r'fr-col-12 fr-col-sm-6 fr-col-md-4'))

            # Loop through each item and extract the relevant information
            for item in accommodation_items:
                try:
                    # Extract the ID from the <a> tag inside the title
                    title_tag = item.find('h3', class_='fr-card__title')
                    id_tag = title_tag.find('a', href=True)
                    accommodation_id = id_tag['href'].split('/')[-1] if id_tag else None

                    # Extract name of the accommodation
                    name = title_tag.text.strip() if title_tag else "No name"

                    # Extract price
                    price_tag = item.find('p', class_='fr-badge')
                    price = price_tag.text.strip() if price_tag else "No price"

                    # Extract location/address
                    location_tag = item.find('p', class_='fr-card__desc')
                    location = location_tag.text.strip() if location_tag else "No location"


                    link = BASE_URL + id_tag['href'] if id_tag else "No link"

                    # Store the extracted details using the ID as the key
                    if accommodation_id:  # Ensure ID is not None
                        accommodations[accommodation_id] = {
                            'name': name,
                            'price': price,
                            'location': location,
                            'link': link
                        }

                except Exception as e:
                    print(f"Error processing accommodation item: {e}")
                    continue

        except Exception as e:
            print(f"Error fetching page {page}: {e}")
            continue

    return accommodations


def is_accommodation_available(accommodation_id):
    """Check if the accommodation is available and get its superficie."""
    detail_url = f"{BASE_URL}/tools/41/accommodations/{accommodation_id}"
    try:
        response = requests.get(detail_url, timeout=10)
        response.raise_for_status()  # Will raise an error for bad status codes

        soup = BeautifulSoup(response.content, 'html.parser')

        # Check for the availability button
        unavailable_button = soup.find('button', title='Indisponible')
        is_available = unavailable_button is None

        # --- NEW CODE TO EXTRACT SUPERFICIE ---
        superficie = 'N/A'  # Default value
        superficie_tag = soup.find('strong', string=re.compile(r'\s*Superficie\s*:\s*'))
        if superficie_tag and superficie_tag.next_sibling:
            superficie = superficie_tag.next_sibling.strip()
        # --- END OF NEW CODE ---

        return accommodation_id, is_available, superficie  # Return all three values

    except requests.RequestException as e:
        print(f"Could not check page for ID {accommodation_id}: {e}")
        return accommodation_id, False, 'N/A'  # Return defaults on error


def check_accommodations_availability(accommodations):
    """Check availability of accommodations and add superficie details."""
    if not accommodations:
        return {}

    available_accommodations = {}
    num_threads = min(10, len(accommodations))
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        # The map function will now return tuples of (id, is_available, superficie)
        results = list(executor.map(is_accommodation_available, accommodations.keys()))

    # --- UPDATED LOGIC TO PROCESS RESULTS ---
    for acc_id, is_available, superficie in results:
        if is_available:
            # If it's available, add the superficie to its details
            accommodations[acc_id]['superficie'] = superficie
            available_accommodations[acc_id] = accommodations[acc_id]
    # --- END OF UPDATED LOGIC ---

    return available_accommodations


def send_email(new_accommodations):
    """Send an email with the new accommodation details, including superficie."""
    msg = MIMEMultipart()
    msg['From'] = GMAIL_USER
    msg['To'] = ', '.join(EMAIL_RECIPIENTS)
    msg['Subject'] = 'New CROUS Accommodation Available'

    # --- UPDATED BODY TO INCLUDE SUPERFICIE ---
    body_lines = [
        f"Name: {details['name']}\n"
        f"Price: {details['price']}\n"
        f"Location: {details['location']}\n"
        f"Superficie: {details.get('superficie', 'N/A')}\n"  # Added this line
        f"Link: {details['link']}\n"
        for details in new_accommodations.values()
    ]
    # --- END OF UPDATE ---

    body = f"New accommodations found:\n\n" + "\n".join(body_lines) + f"\nTotal Available: {len(new_accommodations)}"
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_PASS)
        server.sendmail(GMAIL_USER, EMAIL_RECIPIENTS, msg.as_string())
        server.quit()
        print("Email sent successfully")
    except Exception as e:
        print(f"Failed to send email: {e}")


def main():
    global prev_accommodations
    while True:
        # Fetch current accommodations from the website
        current_accommodations = fetch_accommodations()
        print("Current Accommodations:", current_accommodations)

        # Check availability of accommodations
        available_accommodations = check_accommodations_availability(current_accommodations)
        print("Available accommodations:", available_accommodations)

        # Find new accommodations by comparing the IDs
        new_accommodations = {id_: details for id_, details in available_accommodations.items() if
                              id_ not in prev_accommodations}
        print("New accommodations:", new_accommodations)

        # Send email if there are new accommodations available
        if new_accommodations:
            send_email(new_accommodations)

        # Update the previous accommodations set with the current available IDs
        prev_accommodations.update(available_accommodations.keys())

        time.sleep(CHECK_INTERVAL)


if __name__ == '__main__':
    main()
