import os
from dotenv import load_dotenv
import requests

# Load environment variables from .env file
load_dotenv()

# 1. Your Supabase API Credentials
# Replace these with your actual URL and Anon Key!
SUPABASE_URL =  os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") 


def save_invoice_to_db(invoice_data):
    print("☁️ Sending data to Supabase via API...")
    
    # We target the specific table we created: 'invoices'
    endpoint = f"{SUPABASE_URL}/rest/v1/invoices"
    
    # 2. Set up our security badges
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal" # Tells Supabase we just want a success code back
    }

    # 3. Format the data to match your database column (invoice_data)
    payload = {
        "invoice_data": invoice_data
    }
    
    try:
        # 4. Fire the messenger! 
        response = requests.post(endpoint, headers=headers, json=payload)
        response.raise_for_status() 
        print("✅ Invoice successfully saved to Supabase!")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to save to Supabase: {e}")
        # This will print the exact reason Supabase rejected it (if it does)
        if e.response is not None:
            print(f"Details: {e.response.text}")
        return False
    

def approve_invoice_in_db(invoice_id):
    print(f"☁️ Attempting to approve invoice #{invoice_id} in Supabase...")
    
    # Notice the end of the URL: ?id=eq.{invoice_id}
    # This tells Supabase exactly WHICH row to update (id equals X)
    endpoint = f"{SUPABASE_URL}/rest/v1/invoices?id=eq.{invoice_id}"
    
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    
    # We are only updating the brand new column you just created!
    payload = {
        "status": "approved"
    }
    
    try:
        # We use PATCH to update an existing row, not POST!
        response = requests.patch(endpoint, headers=headers, json=payload)
        response.raise_for_status() 
        print("✅ Invoice successfully approved in database!")
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to update Supabase: {e}")
        return False

def get_all_products():
    """Fetches the entire product catalog from Supabase."""
    url = f"{SUPABASE_URL}/rest/v1/products?select=*"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    
    # We use requests.get() instead of post() because we are reading, not writing!
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json() # Returns a list of dictionaries (your products)
    else:
        print(f"Error fetching products: {response.text}")
        return []

def get_pending_invoices():
    """Fetches all invoices waiting for owner approval."""
    # Notice the query parameter: status=eq.waiting_for_approval
    url = f"{SUPABASE_URL}/rest/v1/invoices?status=eq.waiting_for_approval&select=*"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching pending invoices: {response.text}")
        return []

def reject_invoice_in_db(invoice_id):
    """Updates an invoice status to 'rejected'."""
    url = f"{SUPABASE_URL}/rest/v1/invoices?id=eq.{invoice_id}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    data = {"status": "rejected"}
    response = requests.patch(url, headers=headers, json=data)
    return response.json()

def get_rejected_invoices():
    """Fetches all invoices that need revision by the sales team."""
    url = f"{SUPABASE_URL}/rest/v1/invoices?status=eq.rejected&select=*"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    return []

def update_invoice_in_db(invoice_id, new_invoice_data):
    """Overwrites an existing invoice and sends it back for approval."""
    url = f"{SUPABASE_URL}/rest/v1/invoices?id=eq.{invoice_id}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    # Notice we change the status back to 'waiting_for_approval' so the owner sees it again!
    data = {
        "invoice_data": new_invoice_data,
        "status": "waiting_for_approval"
    }
    response = requests.patch(url, headers=headers, json=data)
    return response.json()

def get_invoice_by_id(invoice_id):
    """Fetches a single invoice perfectly for PDF generation."""
    url = f"{SUPABASE_URL}/rest/v1/invoices?id=eq.{invoice_id}&select=*"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200 and len(response.json()) > 0:
        return response.json()[0] # Return the exact invoice dictionary
    return {"error": "Invoice not found"}

def get_approved_invoices():
    """Fetches all invoices that the Owner has approved and are ready to print."""
    url = f"{SUPABASE_URL}/rest/v1/invoices?status=eq.approved&select=*"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    return []

def add_product_to_db(name, price_cny):
    url = f"{SUPABASE_URL}/rest/v1/products"
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"}
    payload = {"product_name": name, "price_cny": price_cny}
    response = requests.post(url, headers=headers, json=payload)
    return response.status_code == 201

def delete_product_from_db(product_id):
    """Removes an item from the catalog."""
    url = f"{SUPABASE_URL}/rest/v1/products?id=eq.{product_id}"
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    response = requests.delete(url, headers=headers)
    return response.status_code == 204

def update_product_in_db(product_id, name, price_cny):
    """Updates an existing item in the catalog."""
    url = f"{SUPABASE_URL}/rest/v1/products?id=eq.{product_id}"
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"}
    payload = {"product_name": name, "price_cny": price_cny}
    response = requests.patch(url, headers=headers, json=payload)
    return response.status_code == 204 or response.status_code == 200

def add_customer_to_db(name):
    """Adds a new customer name to the CRM list."""
    url = f"{SUPABASE_URL}/rest/v1/customers"
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"}
    payload = {"name": name}
    response = requests.post(url, headers=headers, json=payload)
    return response.status_code == 201

def get_customers_with_counts():
    """Fetches customers and dynamically counts their approved invoices."""
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    
    # 1. Get the list of names
    customers_res = requests.get(f"{SUPABASE_URL}/rest/v1/customers?select=*", headers=headers)
    if customers_res.status_code != 200: return []
    customers = customers_res.json()

    # 2. Get all APPROVED invoices to count them
    invoices_res = requests.get(f"{SUPABASE_URL}/rest/v1/invoices?status=eq.approved&select=invoice_data", headers=headers)
    invoices = invoices_res.json() if invoices_res.status_code == 200 else []

    # 3. Tally up the purchases
    purchase_counts = {}
    for inv in invoices:
        # We look inside the JSON payload for the customer's name
        c_name = inv.get("invoice_data", {}).get("customer_name")
        if c_name:
            purchase_counts[c_name] = purchase_counts.get(c_name, 0) + 1

    # 4. Attach the count to the customer data
    for c in customers:
        c["purchase_count"] = purchase_counts.get(c["name"], 0)
        
    return customers

def get_freight_from_db():
    url = f"{SUPABASE_URL}/rest/v1/freight_services?select=*"
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    response = requests.get(url, headers=headers)
    return response.json() if response.status_code == 200 else []

def add_freight_to_db(name, price_idr):
    url = f"{SUPABASE_URL}/rest/v1/freight_services"
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"}
    payload = {"service_name": name, "price_idr": price_idr}
    response = requests.post(url, headers=headers, json=payload)
    return response.status_code == 201

def delete_freight_from_db(freight_id):
    url = f"{SUPABASE_URL}/rest/v1/freight_services?id=eq.{freight_id}"
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    response = requests.delete(url, headers=headers)
    return response.status_code == 204