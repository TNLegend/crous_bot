
# Accommodation Finder Script for Marseille

This Python script automatically checks for new accommodations listed on the CROUS website for Marseille and sends email notifications when new listings become available. The script is designed to help individuals keep track of available accommodations without manually checking the website.

## Prerequisites

Before running the script, ensure you have Python installed on your machine. The script has been tested with Python 3.8 and above. You also need the following Python libraries:
- `requests`
- `bs4` (BeautifulSoup)
- `python-dotenv`
- `smtplib` (usually included with Python's standard library)

## Installation

First, clone this repository or download the script to your local machine. After obtaining the script, install the required Python libraries using pip:

```bash
pip install requests beautifulsoup4 python-dotenv
```

## Configuration

To run the script, you need to set up an `.env` file in the same directory as the script with the following contents:

```
GMAIL_USER=your-email@gmail.com
GMAIL_PASS=your-app-password
EMAIL_RECIPIENTS=recipient1@example.com,recipient2@example.com
```

**Important**: Replace `your-email@gmail.com` with your Gmail address, and `your-app-password` with a Gmail app password. You can generate an app password by following the instructions [here](https://myaccount.google.com/apppasswords). Replace `recipient1@example.com,recipient2@example.com` with the comma-separated email addresses of the recipients you want to notify.

## Geographical Limitation

Currently, this script only supports checking for accommodations in Marseille as it specifically queries a bounded area on the CROUS website for Marseille. Future updates may include support for other regions.

## Security Note

Since the script involves using sensitive information such as Gmail credentials, it is crucial to secure the `.env` file and ensure it is not shared publicly. Always use a secure method to store and retrieve credentials in production environments.
