from fastapi import FastAPI, HTTPException, Depends
from pymongo import MongoClient
from pydantic import BaseModel
from datetime import datetime

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

# API Models
class OrderRequest(BaseModel):
    email: str

@app.post("/getOrderDetails")
def get_order_details(request: OrderRequest):
    try:
        users_collection = db["users"]
        orders_collection = db["orders"]
        
        user = users_collection.find_one({"email": request.email})
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")
        
        user_id = user["_id"]
        order = orders_collection.find_one({"user_id": user_id})
        if not order:
            raise HTTPException(status_code=404, detail="Order not found for this user.")
        
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
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
