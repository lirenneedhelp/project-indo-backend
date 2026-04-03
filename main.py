from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from database import *
from pydantic import BaseModel
from typing import List
import requests
from dotenv import load_dotenv
import os

load_dotenv()
# Load url from .env
WEBSITE_URL = os.getenv("NETLIFY_URL", "http://localhost:8000")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[WEBSITE_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create a class for login credentials
class LoginCredentials(BaseModel):
    email: str
    password: str

@app.post("/register")
def register_user(credentials: LoginCredentials):
    """Registers a new employee and automatically assigns them the 'sales' role."""
    
    # 1. Tell Supabase Auth to create the secure user credentials
    url = f"{SUPABASE_URL}/auth/v1/signup"
    headers = {"apikey": SUPABASE_KEY, "Content-Type": "application/json"}
    data = {"email": credentials.email, "password": credentials.password}
    res = requests.post(url, headers=headers, json=data)
    
    if res.status_code != 200:
        error_data = res.json()
        real_message = error_data.get("msg", error_data.get("error_description", "Registration failed."))
        raise HTTPException(status_code=400, detail=f"Registration Error: {real_message}")  
          
    # 2. Add their email to our profiles table with the default 'sales' role
    profile_url = f"{SUPABASE_URL}/rest/v1/profiles"
    profile_headers = {
        "apikey": SUPABASE_KEY, 
        "Authorization": f"Bearer {SUPABASE_KEY}", 
        "Content-Type": "application/json"
    }
    profile_data = {"email": credentials.email, "role": "sales"}
    requests.post(profile_url, headers=profile_headers, json=profile_data)
    
    return {"status": "success", "message": "Registration successful! You can now log in."}


@app.post("/login")
def login_user(credentials: LoginCredentials):
    """Logs the user in AND checks if they are an Owner or Sales."""
    url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
    headers = {"apikey": SUPABASE_KEY, "Content-Type": "application/json"}
    data = {"email": credentials.email, "password": credentials.password}
    
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
        
    auth_data = response.json()
    
    # Check the profiles table to see what role this email has
    role_url = f"{SUPABASE_URL}/rest/v1/profiles?email=eq.{credentials.email}&select=role"
    role_res = requests.get(role_url, headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"})
    
    user_role = "sales" # Default fallback
    if role_res.status_code == 200 and len(role_res.json()) > 0:
        user_role = role_res.json()[0]["role"]
        
    # Attach the role to the data we send back to the website
    auth_data["role"] = user_role
    return auth_data


def verify_real_owner(request: Request):
    """The Real Bouncer: Checks token validity AND verifies they have the 'owner' role."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Bouncer says: No secure ID provided.")
    
    token = auth_header.split(" ")[1]
    
    # 1. Verify token is real
    url = f"{SUPABASE_URL}/auth/v1/user"
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Bouncer says: Fake or expired ID. Access Denied.")
        
    user_email = response.json().get("email")
    
    # 2. Verify role is exactly 'owner'
    role_url = f"{SUPABASE_URL}/rest/v1/profiles?email=eq.{user_email}&select=role"
    role_res = requests.get(role_url, headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"})
    
    if role_res.status_code != 200 or len(role_res.json()) == 0 or role_res.json()[0]["role"] != "owner":
        raise HTTPException(status_code=403, detail="Bouncer says: Only the Owner can do this.")
    
@app.get("/products")
def fetch_catalog():
    """API Endpoint for the frontend to get the catalog."""
    products = get_all_products()
    return {"status": "success", "data": products}

# Cart Item Structure
class CartItem(BaseModel):
    id: int
    name: str
    price_cny: float
    qty: float
    isIdr: bool = False

# Payload Structure for the entire invoice submission
class InvoicePayload(BaseModel):
    customer_name: str
    sales_rep_email: str
    exchange_rate_used: float
    items: List[CartItem]
    subtotal_idr: float
    service_fee_idr: float
    final_total_idr: float
    custom_invoice_id: str = ""

class ProductInput(BaseModel):
    name: str
    price_cny: float

class CustomerInput(BaseModel):
    name: str

# The Endpoint that catches the data from the website
@app.post("/submit-invoice")
def submit_cart_invoice(payload: InvoicePayload):
    """Catches the cart data from the frontend and saves it to Supabase."""
    
    # Convert the Pydantic model into a standard Python dictionary
    invoice_data = payload.model_dump()  
    
    # Save it to Supabase (using the function we built yesterday!)
    result = save_invoice_to_db(invoice_data)
    
    if not result:
        return {"error": "Failed to save to database"}
        
    return {"status": "success", "message": "Invoice safely locked in the vault! 🔒"}

@app.get("/pending-invoices")
def fetch_pending():
    """Endpoint for the Owner Portal to get pending invoices."""
    invoices = get_pending_invoices()
    return {"status": "success", "data": invoices}

@app.patch("/approve-invoice/{invoice_id}")
def approve_invoice(invoice_id: int, request: Request):
    # 1. checks the ID first
    verify_real_owner(request)
    
    # 2. if passed, approve it!
    approve_invoice_in_db(invoice_id)
    return {"status": "success", "message": "Invoice approved and locked! 🔒"}

@app.patch("/reject-invoice/{invoice_id}")
def reject_invoice(invoice_id: int, request: Request):
    # 1. checks the ID first
    verify_real_owner(request)
    
    # 2. If passed, reject it!
    reject_invoice_in_db(invoice_id)
    return {"status": "success", "message": "Invoice rejected and sent back to Sales."}

@app.get("/rejected-invoices")
def fetch_rejected():
    """Lets the Sales team see what they need to fix."""
    invoices = get_rejected_invoices()
    return {"status": "success", "data": invoices}

@app.put("/update-invoice/{invoice_id}")
def update_invoice(invoice_id: int, payload: InvoicePayload):
    """Catches the fixed cart data and overwrites the old invoice."""
    invoice_data = payload.model_dump()
    update_invoice_in_db(invoice_id, invoice_data)
    return {"status": "success", "message": "Invoice revised and resubmitted to Owner!"}

@app.get("/invoice/{invoice_id}")
def fetch_single_invoice(invoice_id: int):
    """Retrieves one specific invoice for the PDF Generator."""
    invoice = get_invoice_by_id(invoice_id)
    if "error" in invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return {"status": "success", "data": invoice}

@app.get("/approved-invoices")
def fetch_approved():
    """Endpoint for the Owner to see printable invoices."""
    invoices = get_approved_invoices()
    return {"status": "success", "data": invoices}

@app.post("/products")
def add_product(product: ProductInput):
    success = add_product_to_db(product.name, product.price_cny)
    if success: return {"status": "success", "message": "Product added!"}
    raise HTTPException(status_code=400, detail="Failed to add product.")

@app.delete("/products/{product_id}")
def delete_product(product_id: int):
    success = delete_product_from_db(product_id)
    if success: return {"status": "success", "message": "Product deleted!"}
    raise HTTPException(status_code=400, detail="Failed to delete product.")

@app.put("/products/{product_id}")
def update_product(product_id: int, product: ProductInput):
    success = update_product_in_db(product_id, product.name, product.price_cny)
    if success: return {"status": "success", "message": "Product updated!"}
    raise HTTPException(status_code=400, detail="Failed to update product.")

@app.get("/customers")
def fetch_customers():
    customers = get_customers_with_counts()
    return {"status": "success", "data": customers}

@app.post("/customers")
def add_customer(customer: CustomerInput):
    success = add_customer_to_db(customer.name)
    if success: return {"status": "success", "message": "Customer added!"}
    raise HTTPException(status_code=400, detail="Failed or duplicate customer.")

class FreightInput(BaseModel):
    service_name: str
    price_idr: float

@app.get("/freight")
def get_freight():
    data = get_freight_from_db()
    return {"status": "success", "data": data}

@app.post("/freight")
def add_freight(freight: FreightInput):
    success = add_freight_to_db(freight.service_name, freight.price_idr)
    if success: return {"status": "success", "message": "Freight service added!"}
    raise HTTPException(status_code=400, detail="Failed to add freight service.")

@app.delete("/freight/{freight_id}")
def delete_freight(freight_id: int):
    success = delete_freight_from_db(freight_id)
    if success: return {"status": "success", "message": "Freight service deleted!"}
    raise HTTPException(status_code=400, detail="Failed to delete freight service.")