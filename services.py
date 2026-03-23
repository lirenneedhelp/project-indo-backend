import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import quote

def scrape_price(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    price_element = soup.find("p", class_="price_color")
    if price_element:
        clean_string = re.sub(r'[^\d.]', '', price_element.text)
        return float(clean_string)
    return None

def fetch_exchange_rate():
    url = "https://api.exchangerate-api.com/v4/latest/CNY"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()['rates']['IDR']
    except requests.exceptions.RequestException:
        return None

def calculate_invoice(amount_cny, exchange_rate):
    amount_idr = amount_cny * exchange_rate
    service_fee = amount_idr * 0.10
    final_total = amount_idr + service_fee
    return {
        "base_idr": round(amount_idr, 2),
        "fee_idr": round(service_fee, 2),
        "final_idr": round(final_total, 2),
        "status": "waiting_for_approval" # Added this for our Owner system!
    }

def generate_whatsapp_link(final_price, url, phone_number):
    raw_message = f"Hello! I want to order this item.\nTotal: {final_price:,.2f} IDR.\nLink: {url}"
    return f"https://wa.me/{phone_number}?text={quote(raw_message)}"