from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from services import scrape_price, fetch_exchange_rate, calculate_invoice, generate_whatsapp_link
from database import save_invoice_to_db, approve_invoice_in_db

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, we restrict this. In the sandbox, let everyone in!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/generate-invoice")
def create_invoice(target_url: str):
    business_phone = "6590930239"

    # 1. Scrape
    cny_price = scrape_price(target_url)
    if not cny_price:
        return {"error": "Could not scrape price from that URL."}

    # 2. Get Rate
    rate = fetch_exchange_rate()
    if not rate:
        return {"error": "Currency API is down."}

    # 3. Calculate Math
    invoice_data = calculate_invoice(cny_price, rate)

    # 4. Generate Link
    wa_link = generate_whatsapp_link(invoice_data["final_idr"], target_url, business_phone)

    # 5. Save to Database
    # We combine the scraped data and the math into one big dictionary to save
    full_db_record = {
        "product_url": target_url,
        "scraped_cny": cny_price,
        "exchange_rate": rate,
        "financials": invoice_data
    }
    save_invoice_to_db(full_db_record)

    # 6. Return response to the Sales Rep
    return {
        "status": "success",
        "scraped_cny": cny_price,
        "financials": invoice_data,
        "whatsapp_link": wa_link
    }

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