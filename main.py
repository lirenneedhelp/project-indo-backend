from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from database import (
    save_invoice_to_db, approve_invoice_in_db, get_all_products, 
    get_pending_invoices, reject_invoice_in_db, get_rejected_invoices, update_invoice_in_db
)
from pydantic import BaseModel
from typing import List

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, we restrict this. In the sandbox, let everyone in!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.patch("/approve-invoice/{invoice_id}")
def approve_invoice(
    invoice_id: int, 
    x_user_role: str = Header(default="sales") # FastAPI automatically looks for this Header!
):
    """
    This endpoint checks the user's role before allowing an approval.
    """
    
    # 1. THE BOUNCER LOGIC
    if x_user_role != "owner":
        # If they aren't the owner, we kick them out with a 403 Forbidden error
        raise HTTPException(
            status_code=403, 
            detail="🛑 Sales team cannot approve invoices."
        )
    
    # 2. IF APPROVED, UPDATE THE DATABASE
    success = approve_invoice_in_db(invoice_id)
    
    if not success:
        raise HTTPException(status_code=500, detail="Database update failed.")
        
    return {
        "status": "success", 
        "message": f"Invoice #{invoice_id} has been officially APPROVED by the Owner."
    }

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
    invoice_data = payload.dict()
    
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

@app.patch("/reject-invoice/{invoice_id}")
def reject_invoice(invoice_id: int, request: Request):
    """The Bouncer ensures only the Owner can reject."""
    role = request.headers.get("x-user-role")
    if role != "owner":
        raise HTTPException(status_code=403, detail="Bouncer says: Only the owner can reject invoices.")
    
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
    invoice_data = payload.dict()
    update_invoice_in_db(invoice_id, invoice_data)
    return {"status": "success", "message": "Invoice revised and resubmitted to Owner!"}