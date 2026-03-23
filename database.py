import requests

# 1. Your Supabase API Credentials
# Replace these with your actual URL and Anon Key!
SUPABASE_URL = "https://pmxvnyaqscomvrzhekaw.supabase.co" # (I grabbed this from your previous message!)
SUPABASE_KEY = "sb_secret_-SfXnSI2yUmeSngpOrpKVg_MUeYb2At"

def save_invoice_to_db(invoice_data):
    print("☁️ Sending data to Supabase via API...")
    
    # We target the specific table we created: 'invoices'
    endpoint = f"{SUPABASE_URL}/rest/v1/invoicedb"
    
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
    endpoint = f"{SUPABASE_URL}/rest/v1/invoicedb?id=eq.{invoice_id}"
    
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