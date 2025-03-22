from fastapi import FastAPI, HTTPException
from pymongo import MongoClient
from pydantic import BaseModel
from datetime import datetime
import random, smtplib, ssl
from email.message import EmailMessage

app = FastAPI()

# MongoDB Connection
client = MongoClient("mongodb+srv://reyjohnandraje2002:DarkNikolov17@concentrix.txv3t.mongodb.net/?retryWrites=true&w=majority&appName=Concentrix")
db = client["mixbook_db"]
otp_store = {}  # Temporary storage (should use Redis in production)

# Email Configuration
SENDER_EMAIL = "reyjohnandraje2002@gmail.com"
SENDER_PASSWORD = "stqf trus wvku dykn"

# Function to send OTP email
def send_otp_email(email, otp):
    msg = EmailMessage()
    msg.set_content(f"Your OTP for order verification is: {otp}")
    msg["Subject"] = "Order Verification OTP"
    msg["From"] = SENDER_EMAIL
    msg["To"] = email
    
    context = ssl.create_default_context()
    
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        print(f"[DEBUG] OTP {otp} sent to {email}")  # Debugging
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error sending OTP email: {str(e)}")

# Function to format datetime
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

# API Models
class SendOTPRequest(BaseModel):
    name: str
    order_number: str
    email: str

class VerifyOTPRequest(BaseModel):
    email: str
    otp: int

class GetOrderDetailsRequest(BaseModel):
    email: str

# 1️⃣ Send OTP Endpoint
@app.post("/sendOTP")
def send_otp(request: SendOTPRequest):
    users_collection = db["users"]
    orders_collection = db["orders"]

    # Check if user exists
    user = users_collection.find_one({"name": request.name, "email": request.email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found or email does not match.")
    
    user_id = user["_id"]

    # Check if order exists for the user
    order = orders_collection.find_one({"_id": request.order_number, "user_id": user_id})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found for this user.")

    # Generate OTP and store it
    otp = random.randint(100000, 999999)
    otp_store[request.email] = otp
    send_otp_email(request.email, otp)

    return {"message": "OTP sent to email. Please verify to view order details."}

# 2️⃣ Verify OTP Endpoint
@app.post("/verifyOTP")
def verify_otp(request: VerifyOTPRequest):
    if request.email not in otp_store or otp_store[request.email] != request.otp:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP.")

    return {"message": "OTP verified successfully. You may now retrieve order details."}

# 3️⃣ Get Order Details Endpoint
@app.post("/getOrderDetails")
def get_order_details(request: GetOrderDetailsRequest):
    users_collection = db["users"]
    orders_collection = db["orders"]

    # Find User
    user = users_collection.find_one({"email": request.email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    user_id = user["_id"]

    # Find Order
    order = orders_collection.find_one({"user_id": user_id})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")

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

    return {"message": "Order details retrieved.", "order_details": response_data}
