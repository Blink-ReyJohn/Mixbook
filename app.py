from fastapi import FastAPI, HTTPException, Depends
from pymongo import MongoClient
from pydantic import BaseModel
from datetime import datetime, timedelta
import random, smtplib, ssl
from email.message import EmailMessage

app = FastAPI()

client = MongoClient("mongodb+srv://reyjohnandraje2002:DarkNikolov17@concentrix.txv3t.mongodb.net/?retryWrites=true&w=majority&appName=Concentrix")
db = client["mixbook_db"]

# Function to format dates
def format_datetime(dt):
    if isinstance(dt, str):
        try:
            dt = datetime.strptime(dt, "%Y-%m-%dT%H:%M:%S.%f%z")
        except ValueError:
            try:
                dt = datetime.strptime(dt, "%B %d, %Y %I:%M:%S %p")
            except ValueError:
                raise ValueError(f"Unsupported datetime format: {dt}")
    return dt.strftime("%B %d, %Y %I:%M:%S %p")

# Function to send OTP email
def send_otp_email(email, otp):
    sender_email = "reyjohnandraje2002@gmail.com"
    sender_password = "stqf trus wvku dykn"
    
    msg = EmailMessage()
    msg.set_content(f"Your OTP for order verification is: {otp}")
    msg["Subject"] = "Order Verification OTP"
    msg["From"] = sender_email
    msg["To"] = email
    
    context = ssl.create_default_context()
    
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(sender_email, sender_password)
            server.send_message(msg)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error sending OTP email: {str(e)}")

# API Model
class OrderRequest(BaseModel):
    name: str
    order_number: str
    email: str

@app.post("/getOrderDetails")
def get_order_details(request: OrderRequest):
    try:
        users_collection = db["users"]
        orders_collection = db["orders"]
        
        user = users_collection.find_one({"name": request.name, "email": request.email})
        if not user:
            raise HTTPException(status_code=404, detail="User not found or email does not match.")
        
        order = orders_collection.find_one({"_id": request.order_number, "user_id": user["_id"]})
        if not order:
            raise HTTPException(status_code=404, detail="Order not found for this user.")
        
        otp = random.randint(100000, 999999)
        send_otp_email(request.email, otp)
        
        tracking = order.get("tracking_details", {})
        
        response_data = {
            "order_number": order["_id"],
            "items_ordered": order["items_ordered"],
            "total_price": order["total_price"],
            "last_update": format_datetime(tracking.get("last_update", datetime.utcnow()))
        }
        
        status = tracking.get("status", "Processing")
        
        if status == "Shipped":
            response_data.update({
                "carrier": tracking.get("carrier", "Unknown"),
                "estimated_delivery": tracking.get("estimated_delivery", "Unknown"),
                "current_location": tracking.get("current_location", "Unknown")
            })
        elif status == "Delivered":
            response_data.update({
                "carrier": tracking.get("carrier", "Unknown"),
                "current_location": tracking.get("current_location", "Unknown")
            })
        elif status == "Cancelled":
            response_data.update({
                "reason_of_cancellation": order.get("reason_of_cancellation", "Unknown")
            })
        
        return {"message": "OTP sent to email. Confirm OTP to view order details.", "otp": otp, "order_details": response_data}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
