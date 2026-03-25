from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from database import *
from pydantic import BaseModel
from typing import List
import requests

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, we restrict this. In the sandbox, let everyone in!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create a blueprint for login credentials
class LoginCredentials(BaseModel):
    email: str
    password: str

@app.post("/login")
def login_user(credentials: LoginCredentials):
    """Takes email/password and gets a secure token from Supabase."""
    url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
    headers = {
        "apikey": SUPABASE_KEY,
        "Content-Type": "application/json"
    }
    data = {"email": credentials.email, "password": credentials.password}
    
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code == 200:
        return response.json() # This hands the secure token back to the website!
    else:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    
def verify_real_owner(request: Request):
    """The Real Bouncer: Checks if the token is mathematically valid via Supabase."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Bouncer says: No secure ID provided.")
    
    # Extract the token from the "Bearer <token>" string
    token = auth_header.split(" ")[1]
    
    # Ask the Supabase Auth server if this token is legit
    url = f"{SUPABASE_URL}/auth/v1/user"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {token}"
    }
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Bouncer says: Fake or expired ID. Access Denied.")
    
@app.get("/products")
def fetch_catalog():
    """API Endpoint for the frontend to get the catalog."""
    products = get_all_products()
    return {"status": "success", "data": products}

# 1. Define what a single item in the cart looks like
class CartItem(BaseModel):
    id: int
    name: str
    price_cny: float
    qty: int

# 2. Define what the entire invoice payload looks like
class InvoicePayload(BaseModel):
    exchange_rate_used: float
    items: List[CartItem]
    subtotal_idr: float
    service_fee_idr: float
    final_total_idr: float

# 3. The Endpoint that catches the data from the website
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

