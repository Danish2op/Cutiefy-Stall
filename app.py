import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, date
import io
import base64
from typing import Dict, List, Any
import uuid
import qrcode
from PIL import Image

# 🎨 PAGE CONFIG & STYLING
st.set_page_config(
    page_title="Cutiefy - Stall Management",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 🎨 CUSTOM CSS STYLING
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Dancing+Script:wght@400;500;600;700&family=Poppins:wght@300;400;500;600&display=swap');
    
    .main-header {
        font-family: 'Dancing Script', cursive;
        font-size: 3rem;
        font-weight: 700;
        color: #B85450;
        text-align: center;
        margin: 2rem 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    }
    
    .sub-header {
        font-family: 'Dancing Script', cursive;
        font-size: 2rem;
        font-weight: 600;
        color: #ECD0D4;
        text-align: center;
        margin: 1rem 0;
    }
    
    .section-header {
        font-family: 'Poppins', sans-serif;
        font-size: 1.5rem;
        font-weight: 600;
        color: #B85450;
        border-bottom: 2px solid #ECD0D4;
        padding-bottom: 0.5rem;
        margin: 1.5rem 0;
    }
    
    .brand-button {
        background: linear-gradient(135deg, #ECD0D4, #F5E6E8);
        color: #B85450;
        font-weight: 600;
        border: 2px solid #ECD0D4;
        border-radius: 12px;
        padding: 0.75rem 2rem;
        margin: 0.5rem;
        transition: all 0.3s ease;
        font-family: 'Poppins', sans-serif;
    }
    
    .brand-button:hover {
        background: linear-gradient(135deg, #F5E6E8, #ECD0D4);
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(236, 208, 212, 0.4);
    }
    
    .metric-card {
        background: linear-gradient(135deg, #ECD0D4, #F5E6E8);
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        margin: 1rem 0;
    }
    
    .success-msg {
        background: linear-gradient(135deg, #d4edda, #c3e6cb);
        color: #155724;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #28a745;
        margin: 1rem 0;
    }
    
    .error-msg {
        background: linear-gradient(135deg, #f8d7da, #f1b0b7);
        color: #721c24;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #dc3545;
        margin: 1rem 0;
    }
    
    .logo-container {
        text-align: center;
        margin: 2rem 0;
    }
    
    .logo-container img {
        max-width: 200px;
        height: auto;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    
    .stSelectbox > div > div {
        background-color: #F5E6E8;
        border: 2px solid #ECD0D4;
    }
    
    .stTextInput > div > div > input {
        background-color: #F5E6E8;
        border: 2px solid #ECD0D4;
        color: #B85450;
    }
    
    .stNumberInput > div > div > input {
        background-color: #F5E6E8;
        border: 2px solid #ECD0D4;
        color: #B85450;
    }
</style>
""", unsafe_allow_html=True)

# 🔧 FIREBASE CONFIGURATION - DIRECT CONNECTION
@st.cache_resource

def initialize_firebase():
    if not firebase_admin._apps:
        cred = credentials.Certificate(dict(st.secrets["firebase"]))
        firebase_admin.initialize_app(cred)
    return firestore.client()

# 📧 EMAIL CONFIGURATION - SECURE FOR STREAMLIT CLOUD
def get_email_config():
    if hasattr(st, 'secrets') and 'email' in st.secrets:
        return {
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "email": st.secrets["email"]["address"],
            "password": st.secrets["email"]["password"]
        }
    else:
        # For local development
        return {
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "email": "dsharma.workmain@gmail.com",
            "password": "etth ppbi rmpl ikyc"
        }

EMAIL_CONFIG = get_email_config()

# 🏪 BUSINESS CONFIGURATION
BUSINESS_INFO = {
    "name": "Cutiefy",
    "brand": "Cutiefy",
    "logo_url": "https://i.ibb.co/h1ZWHFbP/Untitled-design-1.png",
    "contact": "Contact: +91-XXXXXXXXXX",
    "address": "Your Stall Address Here"
}

class StallManager:
    def __init__(self):
        try:
            self.db = initialize_firebase()
        except Exception as e:
            st.error(f"Database connection error: {e}")
            st.stop()
            
        if 'cart' not in st.session_state:
            st.session_state.cart = []
        if 'current_customer' not in st.session_state:
            st.session_state.current_customer = {}
    
    # 📦 INVENTORY MANAGEMENT METHODS
    def get_all_items(self) -> List[Dict]:
        """Fetch all items from Firestore"""
        try:
            items_ref = self.db.collection('items')
            items = items_ref.stream()
            return [{'id': item.id, **item.to_dict()} for item in items]
        except Exception as e:
            st.error(f"Error fetching items: {e}")
            return []
    
    def add_item(self, item_data: Dict) -> bool:
        """Add new item to inventory"""
        try:
            # Check if itemID already exists
            existing_items = self.get_all_items()
            if any(item['itemID'] == item_data['itemID'] for item in existing_items):
                st.error(f"Item ID '{item_data['itemID']}' already exists!")
                return False
            
            self.db.collection('items').add(item_data)
            return True
        except Exception as e:
            st.error(f"Error adding item: {e}")
            return False
    
    def update_item(self, doc_id: str, item_data: Dict) -> bool:
        """Update existing item"""
        try:
            self.db.collection('items').document(doc_id).update(item_data)
            return True
        except Exception as e:
            st.error(f"Error updating item: {e}")
            return False
    
    def delete_item(self, doc_id: str) -> bool:
        """Delete item from inventory"""
        try:
            self.db.collection('items').document(doc_id).delete()
            return True
        except Exception as e:
            st.error(f"Error deleting item: {e}")
            return False
    
    # 🧾 BILLING METHODS
    def add_to_cart(self, item: Dict, quantity: int) -> bool:
        """Add item to cart with real-time inventory check"""
        try:
            # Get the latest inventory data to ensure accuracy
            items_ref = self.db.collection('items')
            current_items = list(items_ref.where('itemID', '==', item['itemID']).stream())
            
            if not current_items:
                st.error(f"❌ Item '{item['itemName']}' not found in database!")
                return False
            
            current_item_data = current_items[0].to_dict()
            current_available = current_item_data.get('quantityAvailable', 0)
            
            # Check if item already in cart and calculate total needed
            existing_in_cart = sum(cart_item['quantity'] for cart_item in st.session_state.cart 
                                 if cart_item['itemID'] == item['itemID'])
            total_needed = existing_in_cart + quantity
            
            if current_available < total_needed:
                available_to_add = max(0, current_available - existing_in_cart)
                if available_to_add > 0:
                    st.error(f"❌ Only {available_to_add} more items available! (You already have {existing_in_cart} in cart)")
                else:
                    st.error(f"❌ No more items available! (You already have {existing_in_cart} in cart, only {current_available} in stock)")
                return False
            
            # Add to cart
            cart_item = {
                'itemID': item['itemID'],
                'itemName': item['itemName'],
                'salePrice': current_item_data['salePrice'],  # Use latest price
                'quantity': quantity,
                'total': current_item_data['salePrice'] * quantity
            }
            
            # Check if item already in cart
            existing_index = next((i for i, cart_item_check in enumerate(st.session_state.cart) 
                                  if cart_item_check['itemID'] == item['itemID']), None)
            
            if existing_index is not None:
                st.session_state.cart[existing_index]['quantity'] += quantity
                st.session_state.cart[existing_index]['total'] = (
                    st.session_state.cart[existing_index]['quantity'] * 
                    current_item_data['salePrice']
                )
            else:
                st.session_state.cart.append(cart_item)
            
            return True
            
        except Exception as e:
            st.error(f"Error adding to cart: {e}")
            return False
    
    def remove_from_cart(self, index: int):
        """Remove item from cart"""
        if 0 <= index < len(st.session_state.cart):
            st.session_state.cart.pop(index)
    
    def calculate_cart_total(self) -> float:
        """Calculate total cart amount"""
        return sum(item['total'] for item in st.session_state.cart)
    
    def validate_cart_inventory(self) -> bool:
        """Validate that all cart items have sufficient inventory"""
        try:
            for cart_item in st.session_state.cart:
                items_ref = self.db.collection('items')
                current_items = list(items_ref.where('itemID', '==', cart_item['itemID']).stream())
                
                if not current_items:
                    st.error(f"❌ Item '{cart_item['itemName']}' no longer exists!")
                    return False
                
                current_available = current_items[0].to_dict().get('quantityAvailable', 0)
                if current_available < cart_item['quantity']:
                    st.error(f"❌ Insufficient stock for '{cart_item['itemName']}': Need {cart_item['quantity']}, Available {current_available}")
                    return False
            
            return True
        except Exception as e:
            st.error(f"Error validating inventory: {e}")
            return False
    
    def apply_discount(self, subtotal: float, discount_type: str, discount_value: float) -> float:
        """Apply discount to subtotal"""
        if discount_type == "Percentage":
            return subtotal * (discount_value / 100)
        else:  # Flat discount
            return min(discount_value, subtotal)
    
    def save_sale(self, customer_data: Dict, cart_items: List, subtotal: float, 
                  discount: float, total_paid: float) -> str:
        """Save sale to Firestore and update inventory quantities"""
        try:
            # Enhance cart items with ACCURATE profit calculation considering discount
            enhanced_cart = []
            items_ref = self.db.collection('items')
            total_cost = 0
            
            for cart_item in cart_items:
                # Get current item data including purchase price
                current_items = list(items_ref.where('itemID', '==', cart_item['itemID']).stream())
                if current_items:
                    item_data = current_items[0].to_dict()
                    purchase_price = item_data.get('purchasePrice', 0)
                    
                    enhanced_item = cart_item.copy()
                    enhanced_item['purchasePrice'] = purchase_price
                    
                    # Calculate item cost and profit BEFORE discount
                    item_cost = purchase_price * cart_item['quantity']
                    total_cost += item_cost
                    
                    # Store the cost for this item
                    enhanced_item['totalCost'] = item_cost
                    enhanced_cart.append(enhanced_item)
                else:
                    # Fallback if item not found
                    enhanced_item = cart_item.copy()
                    enhanced_item['purchasePrice'] = 0
                    enhanced_item['totalCost'] = 0
                    enhanced_cart.append(enhanced_item)
            
            # Calculate ACCURATE total profit: Amount Actually Received - Total Cost
            total_profit = total_paid - total_cost
            
            # Distribute profit proportionally among items based on their revenue contribution
            if subtotal > 0:
                for item in enhanced_cart:
                    # Calculate item's share of total revenue
                    item_revenue_share = item['total'] / subtotal
                    
                    # Assign proportional profit to this item
                    item['totalProfit'] = total_profit * item_revenue_share
                    
                    # Calculate effective profit per unit after discount
                    if item['quantity'] > 0:
                        item['profitPerUnit'] = item['totalProfit'] / item['quantity']
                    else:
                        item['profitPerUnit'] = 0
            
            sale_data = {
                'customerName': customer_data['name'],
                'customerEmail': customer_data['email'],
                'customerPhone': customer_data['phone'],
                'cart': enhanced_cart,  # Now includes profit data
                'subtotal': subtotal,
                'discount': discount,
                'totalPaid': total_paid,
                'totalProfit': total_profit,  # Add total profit to sale record
                'createdAt': datetime.now(),
                'saleID': str(uuid.uuid4())[:8].upper()
            }
            
            # Update inventory for each cart item
            for cart_item in enhanced_cart:
                # Find the item document
                current_items = list(items_ref.where('itemID', '==', cart_item['itemID']).stream())
                if current_items:
                    item_doc = current_items[0]
                    current_data = item_doc.to_dict()
                    current_qty = current_data.get('quantityAvailable', 0)
                    new_qty = max(0, current_qty - cart_item['quantity'])
                    
                    # Update inventory
                    items_ref.document(item_doc.id).update({'quantityAvailable': new_qty})
                    
                    # Stock alerts
                    if new_qty == 0:
                        st.warning(f"⚠️ Item '{cart_item['itemName']}' is now out of stock!")
                    elif new_qty < 10:
                        st.warning(f"⚠️ Low stock alert: '{cart_item['itemName']}' has only {new_qty} items left!")
            
            # Save the sale
            self.db.collection('sales').add(sale_data)
            
            st.success("✅ Inventory updated automatically!")
            st.info(f"💰 Accurate Profit on this sale: ₹{total_profit:.2f}")
            st.info(f"💸 Total Cost: ₹{total_cost:.2f} | 💵 Amount Received: ₹{total_paid:.2f}")
            return sale_data['saleID']
            
        except Exception as e:
            st.error(f"Error saving sale and updating inventory: {e}")
            return None
    
    def send_email_receipt(self, customer_email: str, customer_name: str, 
                          cart_items: List, subtotal: float, discount: float, 
                          total_paid: float, sale_id: str, delivery_charges: float = 0.0) -> bool:
        """Send beautiful HTML email receipt with static QR code for payment and delivery charges"""
        try:
            st.info(f"📧 Sending email to {customer_email}...")

            # Use static QR code image and provided UPI ID
            upi_id = "sakshi.sharma28011@okhdfcbank"
            qr_img_url = "https://i.ibb.co/jkx87sVM/qr.jpg"
            qr_img_html = f'<img src="{qr_img_url}" alt="UPI QR Code" style="max-width:180px; margin: 20px auto; display:block;" />'

            # Create HTML email template
            html_template = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset='utf-8'>
                <meta name='viewport' content='width=device-width, initial-scale=1.0'>
                <title>Receipt - {BUSINESS_INFO['brand']}</title>
                <style>
                    body {{ font-family: 'Poppins', Arial, sans-serif; background-color: #f5f5f5; margin: 0; padding: 20px; }}
                    .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 18px; overflow: hidden; box-shadow: 0 8px 32px rgba(184,84,80,0.10); animation: fadeIn 1.2s; }}
                    .header {{ background: linear-gradient(135deg, #ECD0D4, #F5E6E8); padding: 36px 30px 24px 30px; text-align: center; animation: slideDown 1.2s; }}
                    .logo {{ max-width: 120px; height: auto; border-radius: 12px; box-shadow: 0 2px 8px rgba(184,84,80,0.10); animation: bounceIn 1.2s; }}
                    .brand-name {{ font-size: 2.7rem; color: #B85450; margin: 18px 0 5px 0; font-weight: bold; font-family: 'Dancing Script', cursive; letter-spacing: 1px; }}
                    .content {{ padding: 36px 30px 30px 30px; animation: fadeIn 1.5s; }}
                    .receipt-title {{ font-size: 2rem; color: #B85450; margin-bottom: 22px; text-align: center; font-family: 'Dancing Script', cursive; letter-spacing: 1px; }}
                    .customer-info {{ background: #F5E6E8; padding: 22px; border-radius: 10px; margin-bottom: 28px; box-shadow: 0 2px 8px rgba(236,208,212,0.10); animation: fadeIn 2s; }}
                    .items-table {{ width: 100%; border-collapse: collapse; margin: 24px 0; }}
                    .items-table th, .items-table td {{ padding: 13px; text-align: left; border-bottom: 1px solid #ECD0D4; }}
                    .items-table th {{ background: #ECD0D4; color: #B85450; font-weight: bold; }}
                    .total-section {{ background: #F5E6E8; padding: 22px; border-radius: 10px; margin-top: 28px; box-shadow: 0 2px 8px rgba(236,208,212,0.10); animation: fadeIn 2.2s; }}
                    .total-row {{ display: flex; justify-content: space-between; margin: 10px 0; font-size: 1.08rem; }}
                    .final-total {{ font-size: 1.4rem; font-weight: bold; color: #B85450; border-top: 2px solid #ECD0D4; padding-top: 18px; margin-top: 18px; letter-spacing: 1px; }}
                    .footer {{ background: #ECD0D4; padding: 24px; text-align: center; color: #B85450; animation: fadeIn 2.5s; }}
                    .thank-you {{ font-size: 1.3rem; font-weight: bold; margin-bottom: 12px; font-family: 'Dancing Script', cursive; animation: popIn 2.2s; }}
                    .qr-section {{ text-align:center; margin-top:36px; animation: fadeIn 2.2s; }}
                    .qr-section img {{ max-width:180px; margin: 0 auto 10px auto; display:block; border-radius: 16px; box-shadow: 0 4px 16px rgba(184,84,80,0.10); animation: bounceIn 1.5s; }}
                    .pay-instructions {{ color:#B85450; font-weight:bold; margin: 8px 0 0 0; font-size: 1.08rem; }}
                    .upi-id {{ color:#B85450; font-size: 1.1rem; font-weight: bold; margin-bottom: 0; }}
                    @keyframes fadeIn {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
                    @keyframes slideDown {{ from {{ transform: translateY(-40px); opacity: 0; }} to {{ transform: translateY(0); opacity: 1; }} }}
                    @keyframes bounceIn {{ 0% {{ transform: scale(0.7); opacity: 0; }} 60% {{ transform: scale(1.1); opacity: 1; }} 100% {{ transform: scale(1); }} }}
                    @keyframes popIn {{ 0% {{ transform: scale(0.7); opacity: 0; }} 80% {{ transform: scale(1.1); opacity: 1; }} 100% {{ transform: scale(1); }} }}
                    /* Responsive */
                    @media (max-width: 650px) {{
                        .container, .content, .header, .footer {{ padding: 10px !important; }}
                        .brand-name {{ font-size: 2rem; }}
                        .receipt-title {{ font-size: 1.3rem; }}
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <img src="{BUSINESS_INFO['logo_url']}" alt="Logo" class="logo">
                        <div class="brand-name">{BUSINESS_INFO['brand']}</div>
                    </div>
                    <div class="content">
                        <h2 class="receipt-title">🧾 Purchase Receipt</h2>
                        <div class="customer-info">
                            <h3 style="margin-top: 0; color: #B85450;">Customer Details</h3>
                            <p><strong>Name:</strong> {customer_name}</p>
                            <p><strong>Email:</strong> {customer_email}</p>
                            <p><strong>Receipt ID:</strong> {sale_id}</p>
                            <p><strong>Date:</strong> {datetime.now().strftime("%B %d, %Y at %I:%M %p")}</p>
                        </div>
                        <h3 style="color: #B85450;">Items Purchased</h3>
                        <table class="items-table">
                            <thead>
                                <tr>
                                    <th>Item</th>
                                    <th>Qty</th>
                                    <th>Price</th>
                                    <th>Total</th>
                                </tr>
                            </thead>
                            <tbody>
            """
            # Add cart items to email
            for item in cart_items:
                html_template += f"""
                                <tr>
                                    <td>{item['itemName']}</td>
                                    <td>{item['quantity']}</td>
                                    <td>₹{item['salePrice']:.2f}</td>
                                    <td>₹{item['total']:.2f}</td>
                                </tr>
                """
            html_template += f"""
                            </tbody>
                        </table>
                        <div class="total-section">
                            <div class="total-row">
                                <span>Subtotal:</span>
                                <span>₹{subtotal:.2f}</span>
                            </div>
                            <div class="total-row">
                                <span>Discount:</span>
                                <span>-₹{discount:.2f}</span>
                            </div>
                            <div class="total-row">
                                <span>Delivery Charges:</span>
                                <span>₹{delivery_charges:.2f}</span>
                            </div>
                            <div class="total-row final-total">
                                <span>Total Paid:</span>
                                <span>₹{total_paid:.2f}</span>
                            </div>
                        </div>
                        <div class="qr-section">
                            <h3 style="color:#B85450;">Pay via UPI</h3>
                            {qr_img_html}
                            <div class="upi-id">UPI ID: {upi_id}</div>
                            <div class="pay-instructions">Please scan the QR code above or pay to the UPI ID. After payment, reply to this email with a screenshot of your payment showing the <b>UPIRF number</b> for confirmation.</div>
                        </div>
                    </div>
                    <div class="footer">
                        <div class="thank-you">Thank you for shopping with us! 💖</div>
                        <p>{BUSINESS_INFO['contact']}</p>
                        <p>{BUSINESS_INFO['address']}</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Send email with detailed error handling
            msg = MIMEMultipart('alternative')
            msg['From'] = EMAIL_CONFIG['email']
            msg['To'] = customer_email
            msg['Subject'] = f"Receipt from {BUSINESS_INFO['brand']}"
            
            html_part = MIMEText(html_template, 'html')
            msg.attach(html_part)
            
            st.info("🔗 Connecting to Gmail SMTP server...")
            server = smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'])
            server.starttls()
            
            st.info("🔐 Logging into Gmail...")
            server.login(EMAIL_CONFIG['email'], EMAIL_CONFIG['password'])
            
            st.info("📤 Sending email...")
            server.send_message(msg)
            server.quit()
            
            st.success("✅ Email sent successfully!")
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            st.error(f"❌ Gmail Authentication Failed: {e}")
            st.error("Check if your app password is correct and 2FA is enabled")
            return False
        except smtplib.SMTPException as e:
            st.error(f"❌ SMTP Error: {e}")
            return False
        except Exception as e:
            st.error(f"❌ Email Error: {e}")
            st.error("Make sure your Gmail credentials are correct")
            return False
    
    # 📊 REPORTING METHODS
    def get_daily_sales(self, selected_date: date) -> List[Dict]:
        """Get all sales for a specific date"""
        try:
            start_date = datetime.combine(selected_date, datetime.min.time())
            end_date = datetime.combine(selected_date, datetime.max.time())
            
            sales_ref = self.db.collection('sales')
            sales = sales_ref.where('createdAt', '>=', start_date).where('createdAt', '<=', end_date).stream()
            
            return [{'id': sale.id, **sale.to_dict()} for sale in sales]
        except Exception as e:
            st.error(f"Error fetching daily sales: {e}")
            return []
    
    def generate_daily_report(self, selected_date: date) -> bytes:
        """Generate Excel report for daily sales with ALWAYS ACCURATE profit analysis"""
        sales = self.get_daily_sales(selected_date)
        
        if not sales:
            return None
        
        # Get current inventory for fallback profit calculations
        items_ref = self.db.collection('items')
        current_inventory = {item.to_dict()['itemID']: item.to_dict() for item in items_ref.stream()}
        
        # Prepare data for Excel with ALWAYS ACCURATE profit calculations
        report_data = []
        total_revenue = 0
        total_profit = 0
        total_cost = 0
        
        for sale in sales:
            sale_total_paid = sale['totalPaid']
            sale_discount = sale.get('discount', 0)
            sale_subtotal = sale.get('subtotal', sale_total_paid + sale_discount)
            
            # ALWAYS recalculate profit accurately - ignore stored values
            sale_cost = 0
            for item in sale['cart']:
                item_id = item['itemID']
                item_purchase_price = item.get('purchasePrice', 0)
                
                # Fallback to current inventory if no purchase price in sale record
                if item_purchase_price == 0 and item_id in current_inventory:
                    item_purchase_price = current_inventory[item_id].get('purchasePrice', 0)
                
                sale_cost += item_purchase_price * item['quantity']
            
            # ACCURATE profit = Amount actually received - Total cost
            sale_profit = sale_total_paid - sale_cost
            
            for item in sale['cart']:
                # Get accurate item data
                item_purchase_price = item.get('purchasePrice', 0)
                
                # Fallback to current inventory if no purchase price in sale record
                if item_purchase_price == 0 and item['itemID'] in current_inventory:
                    item_purchase_price = current_inventory[item['itemID']].get('purchasePrice', 0)
                
                # Calculate item cost
                item_total_cost = item_purchase_price * item['quantity']
                
                # Calculate accurate item profit (proportional share of total sale profit)
                if sale_subtotal > 0:
                    item_revenue_share = item['total'] / sale_subtotal
                    item_total_profit = sale_profit * item_revenue_share
                    item_profit_per_unit = item_total_profit / item['quantity'] if item['quantity'] > 0 else 0
                else:
                    item_total_profit = 0
                    item_profit_per_unit = 0
                
                # Calculate profit margin based on actual revenue received (after discount effect)
                effective_item_revenue = item['total'] * (sale_total_paid / sale_subtotal) if sale_subtotal > 0 else item['total']
                profit_margin = (item_total_profit / effective_item_revenue * 100) if effective_item_revenue > 0 else 0
                
                report_data.append({
                    'Receipt ID': sale['saleID'],
                    'Time': sale['createdAt'].strftime("%I:%M %p"),
                    'Customer Name': sale['customerName'],
                    'Customer Email': sale['customerEmail'],
                    'Customer Phone': sale['customerPhone'],
                    'Item Name': item['itemName'],
                    'Item ID': item['itemID'],
                    'Quantity': item['quantity'],
                    'Purchase Price (₹)': f"₹{item_purchase_price:.2f}",
                    'Sale Price (₹)': f"₹{item['salePrice']:.2f}",
                    'Item Revenue (₹)': f"₹{item['total']:.2f}",
                    'Item Cost (₹)': f"₹{item_total_cost:.2f}",
                    'Item Profit (₹)': f"₹{item_total_profit:.2f}",
                    'Profit Margin (%)': f"{profit_margin:.1f}%",
                    'Sale Subtotal (₹)': f"₹{sale_subtotal:.2f}",
                    'Sale Discount (₹)': f"₹{sale_discount:.2f}",
                    'Sale Total Paid (₹)': f"₹{sale_total_paid:.2f}",
                    'Sale Profit (₹)': f"₹{sale_profit:.2f}"
                })
            
            total_revenue += sale_total_paid
            total_profit += sale_profit
            total_cost += sale_cost
        
        # Add summary rows with accurate calculations
        report_data.append({
            'Receipt ID': '=== DAILY SUMMARY ===',
            'Time': '',
            'Customer Name': f'📊 Total Sales: {len(sales)}',
            'Customer Email': f'💰 Total Revenue: ₹{total_revenue:.2f}',
            'Customer Phone': f'💸 Total Cost: ₹{total_cost:.2f}',
            'Item Name': f'💵 Total Profit: ₹{total_profit:.2f}',
            'Item ID': f'📈 Profit Margin: {((total_profit / total_revenue) * 100):.1f}%' if total_revenue > 0 else '0.0%',
            'Quantity': f'✅ Calculation: Revenue({total_revenue:.2f}) - Cost({total_cost:.2f}) = Profit({total_profit:.2f})',
            'Purchase Price (₹)': '',
            'Sale Price (₹)': '',
            'Item Revenue (₹)': '',
            'Item Cost (₹)': '',
            'Item Profit (₹)': '',
            'Profit Margin (%)': '',
            'Sale Subtotal (₹)': '',
            'Sale Discount (₹)': '',
            'Sale Total Paid (₹)': '',
            'Sale Profit (₹)': ''
        })
        
        # Create Excel file
        df = pd.DataFrame(report_data)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            sheet_name = f'Sales_Profit_{selected_date.strftime("%Y-%m-%d")}'
            df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        return output.getvalue()

def main():
    # Initialize the stall manager
    manager = StallManager()
    
    # 🏠 MAIN LANDING PAGE
    if 'page' not in st.session_state:
        st.session_state.page = 'home'
    
    # Sidebar Navigation
    st.sidebar.markdown("""
    <div class="logo-container">
        <img src="https://i.ibb.co/h1ZWHFbP/Untitled-design-1.png" alt="Cutiefy Logo">
    </div>
    """, unsafe_allow_html=True)
    
    st.sidebar.markdown('<h2 class="sub-header">🏪 Navigation</h2>', unsafe_allow_html=True)
    
    if st.sidebar.button("🏠 Home", key="nav_home"):
        st.session_state.page = 'home'
    if st.sidebar.button("📦 Manage Inventory", key="nav_inventory"):
        st.session_state.page = 'inventory'
    if st.sidebar.button("🧾 Generate Bill", key="nav_billing"):
        st.session_state.page = 'billing'
    if st.sidebar.button("📊 Daily Reports", key="nav_reports"):
        st.session_state.page = 'reports'
    
    # 🏠 HOME PAGE
    if st.session_state.page == 'home':
        # Logo and Header
        st.markdown("""
        <div class="logo-container">
            <img src="https://i.ibb.co/h1ZWHFbP/Untitled-design-1.png" alt="Cutiefy Logo">
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown('<h1 class="main-header">Welcome to Cutiefy</h1>', unsafe_allow_html=True)
        st.markdown('<h2 class="sub-header">Stall Management System</h2>', unsafe_allow_html=True)
        
        # Main action buttons
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            if st.button("📦 Manage Inventory", key="home_inventory", help="Add, edit, and manage your store items"):
                st.session_state.page = 'inventory'
                st.rerun()
            
            if st.button("🧾 Generate Bill for Customer", key="home_billing", help="Create bills and send receipts"):
                st.session_state.page = 'billing'
                st.rerun()
            
            if st.button("📊 View Daily Reports", key="home_reports", help="Download sales reports"):
                st.session_state.page = 'reports'
                st.rerun()
    
    # 📦 INVENTORY MANAGEMENT PAGE
    elif st.session_state.page == 'inventory':
        st.markdown('<h1 class="section-header">📦 Inventory Management</h1>', unsafe_allow_html=True)
        
        # Get all items
        items = manager.get_all_items()
        
        # Add new item section
        with st.expander("➕ Add New Item", expanded=False):
            with st.form("add_item_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    item_name = st.text_input("Item Name*", placeholder="e.g., Cute Pink Notebook")
                    item_id = st.text_input("Item ID*", placeholder="e.g., NB001")
                    purchase_price = st.number_input("Purchase Price (₹)*", min_value=0.0, step=0.01)
                
                with col2:
                    sale_price = st.number_input("Sale Price (₹)*", min_value=0.0, step=0.01)
                    quantity = st.number_input("Quantity Available*", min_value=0, step=1)
                
                submitted = st.form_submit_button("Add Item")
                
                if submitted:
                    if item_name and item_id and purchase_price > 0 and sale_price > 0:
                        item_data = {
                            'itemName': item_name,
                            'itemID': item_id,
                            'purchasePrice': purchase_price,
                            'salePrice': sale_price,
                            'quantityAvailable': quantity
                        }
                        
                        if manager.add_item(item_data):
                            st.success(f"✅ Item '{item_name}' added successfully!")
                            st.rerun()
                    else:
                        st.error("Please fill in all required fields correctly.")
        
        # Display existing items
        if items:
            st.markdown('<h3 class="section-header">Current Inventory</h3>', unsafe_allow_html=True)
            
            # Display metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Items", len(items))
            with col2:
                total_value = sum(item['salePrice'] * item['quantityAvailable'] for item in items)
                st.metric("Inventory Value", f"₹{total_value:.2f}")
            with col3:
                low_stock = sum(1 for item in items if item['quantityAvailable'] < 10)
                st.metric("Low Stock Items", low_stock)
            with col4:
                avg_price = sum(item['salePrice'] for item in items) / len(items)
                st.metric("Avg Price", f"₹{avg_price:.2f}")
            
            # Items table with edit/delete options
            for i, item in enumerate(items):
                with st.container():
                    col1, col2, col3, col4, col5, col6, col7 = st.columns([2, 1.5, 1, 1, 1, 1, 1])
                    
                    with col1:
                        st.write(f"**{item['itemName']}**")
                    with col2:
                        st.write(item['itemID'])
                    with col3:
                        st.write(f"₹{item['purchasePrice']:.2f}")
                    with col4:
                        st.write(f"₹{item['salePrice']:.2f}")
                    with col5:
                        color = "red" if item['quantityAvailable'] < 10 else "green"
                        st.markdown(f"<span style='color: {color}'>{item['quantityAvailable']}</span>", unsafe_allow_html=True)
                    with col6:
                        if st.button("✏️", key=f"edit_{i}", help="Edit item"):
                            st.session_state[f'edit_item_{i}'] = True
                    with col7:
                        if st.button("🗑️", key=f"delete_{i}", help="Delete item"):
                            if manager.delete_item(item['id']):
                                st.success(f"✅ Item '{item['itemName']}' deleted!")
                                st.rerun()
                    
                    # Edit form (appears when edit button is clicked)
                    if st.session_state.get(f'edit_item_{i}', False):
                        with st.form(f"edit_form_{i}"):
                            st.markdown(f"**Editing: {item['itemName']}**")
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                new_name = st.text_input("Item Name", value=item['itemName'])
                                new_purchase = st.number_input("Purchase Price", value=item['purchasePrice'], min_value=0.0, step=0.01)
                                new_sale = st.number_input("Sale Price", value=item['salePrice'], min_value=0.0, step=0.01)
                            
                            with col2:
                                new_quantity = st.number_input("Quantity", value=item['quantityAvailable'], min_value=0, step=1)
                            
                            col_save, col_cancel = st.columns(2)
                            with col_save:
                                if st.form_submit_button("💾 Save Changes"):
                                    update_data = {
                                        'itemName': new_name,
                                        'purchasePrice': new_purchase,
                                        'salePrice': new_sale,
                                        'quantityAvailable': new_quantity
                                    }
                                    if manager.update_item(item['id'], update_data):
                                        st.success("✅ Item updated successfully!")
                                        st.session_state[f'edit_item_{i}'] = False
                                        st.rerun()
                            with col_cancel:
                                if st.form_submit_button("❌ Cancel"):
                                    st.session_state[f'edit_item_{i}'] = False
                                    st.rerun()
                    
                    st.divider()
        else:
            st.info("No items in inventory yet. Add your first item above!")
    
    # 🧾 BILLING PAGE
    elif st.session_state.page == 'billing':
        st.markdown('<h1 class="section-header">🧾 Generate Customer Bill</h1>', unsafe_allow_html=True)
        
        # Customer Details Section
        st.markdown('<h3 class="section-header">👤 Customer Information</h3>', unsafe_allow_html=True)
        with st.form("customer_info"):
            col1, col2 = st.columns(2)
            with col1:
                customer_name = st.text_input("Customer Name*", placeholder="Enter customer name")
                customer_email = st.text_input("Email Address*", placeholder="customer@email.com")
            with col2:
                customer_phone = st.text_input("Phone Number*", placeholder="+91-XXXXXXXXXX")
            
            if st.form_submit_button("💾 Save Customer Info"):
                if customer_name and customer_email and customer_phone:
                    st.session_state.current_customer = {
                        'name': customer_name,
                        'email': customer_email,
                        'phone': customer_phone
                    }
                    st.success("✅ Customer information saved!")
                else:
                    st.error("Please fill in all customer details.")
        
        # Add Items to Cart Section
        st.markdown('<h3 class="section-header">🛒 Add Items to Cart</h3>', unsafe_allow_html=True)
        
        items = manager.get_all_items()
        if items:
            with st.form("add_to_cart"):
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    # Create searchable dropdown
                    item_options = [f"{item['itemName']} (ID: {item['itemID']})" for item in items]
                    selected_item_text = st.selectbox("Select Item", item_options)
                
                with col2:
                    quantity = st.number_input("Quantity", min_value=1, value=1, step=1)
                
                with col3:
                    st.write("")  # Space
                    st.write("")  # Space
                    add_to_cart = st.form_submit_button("➕ Add to Cart")
                
                if add_to_cart and selected_item_text:
                    # Find the selected item
                    selected_item = next(item for item in items if f"{item['itemName']} (ID: {item['itemID']})" == selected_item_text)
                    
                    # Add to cart with real-time inventory check
                    if manager.add_to_cart(selected_item, quantity):
                        st.success(f"✅ Added {quantity} x {selected_item['itemName']} to cart!")
                        st.rerun()
        
        # Display Cart
        if st.session_state.cart:
            st.markdown('<h3 class="section-header">🛒 Current Cart</h3>', unsafe_allow_html=True)
            
            for i, cart_item in enumerate(st.session_state.cart):
                col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 1])
                
                with col1:
                    st.write(f"**{cart_item['itemName']}** (ID: {cart_item['itemID']})")
                with col2:
                    st.write(f"₹{cart_item['salePrice']:.2f}")
                with col3:
                    st.write(f"Qty: {cart_item['quantity']}")
                with col4:
                    st.write(f"₹{cart_item['total']:.2f}")
                with col5:
                    if st.button("🗑️", key=f"remove_cart_{i}", help="Remove from cart"):
                        manager.remove_from_cart(i)
                        st.rerun()
            
            st.divider()
            
            # Cart Summary and Checkout
            subtotal = manager.calculate_cart_total()
            
            st.markdown('<h3 class="section-header">💰 Billing Summary</h3>', unsafe_allow_html=True)
            
            # Discount section
            col1, col2, col3 = st.columns(3)
            with col1:
                discount_type = st.selectbox("Discount Type", ["None", "Percentage", "Flat Amount"])
            with col2:
                discount_value = st.number_input("Discount Value", min_value=0.0, step=0.01) if discount_type != "None" else 0
            with col3:
                delivery_charges = st.number_input("Delivery Charges", min_value=0.0, step=0.01, value=0.0)
            # Calculate totals
            discount_amount = 0
            if discount_type != "None":
                discount_amount = manager.apply_discount(subtotal, discount_type, discount_value)
            final_total = subtotal - discount_amount + delivery_charges
            # Display totals
            col1, col2 = st.columns(2)
            with col2:
                st.markdown(f"""
                <div class="metric-card">
                    <div style="display: flex; justify-content: space-between; margin: 5px 0;">
                        <span>Subtotal:</span>
                        <span>₹{subtotal:.2f}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin: 5px 0;">
                        <span>Discount:</span>
                        <span>-₹{discount_amount:.2f}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin: 5px 0;">
                        <span>Delivery Charges:</span>
                        <span>₹{delivery_charges:.2f}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin: 15px 0 5px 0; font-size: 1.2rem; font-weight: bold; border-top: 2px solid #B85450; padding-top: 10px;">
                        <span>Total:</span>
                        <span>₹{final_total:.2f}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            # Checkout button
            if st.button("🎯 Generate Bill & Send Receipt", disabled=not st.session_state.current_customer):
                if st.session_state.current_customer:
                    # Validate inventory before processing sale
                    if manager.validate_cart_inventory():
                        # Save sale to database and update inventory
                        sale_id = manager.save_sale(
                            st.session_state.current_customer,
                            st.session_state.cart,
                            subtotal,
                            discount_amount,
                            final_total
                        )
                        if sale_id:
                            # Send email receipt with delivery charges and QR code
                            email_sent = manager.send_email_receipt(
                                st.session_state.current_customer['email'],
                                st.session_state.current_customer['name'],
                                st.session_state.cart,
                                subtotal,
                                discount_amount,
                                final_total,
                                sale_id,
                                delivery_charges
                            )
                            if email_sent:
                                st.success(f"✅ Bill generated successfully! Receipt sent to {st.session_state.current_customer['email']}")
                                st.success(f"🆔 Sale ID: {sale_id}")
                            else:
                                st.warning(f"✅ Bill saved (ID: {sale_id}) but email failed to send. Please check email configuration.")
                            # Clear cart and customer info
                            st.session_state.cart = []
                            st.session_state.current_customer = {}
                            st.rerun()
                    else:
                        st.error("❌ Cannot complete sale - inventory validation failed. Please update your cart.")
                else:
                    st.error("Please enter customer information first!")
        
        else:
            st.info("Cart is empty. Add items to proceed with billing.")
    
    # 📊 REPORTS PAGE
    elif st.session_state.page == 'reports':
        st.markdown('<h1 class="section-header">📊 Daily Sales Reports</h1>', unsafe_allow_html=True)
        
        # Date selection
        selected_date = st.date_input("Select Date for Report", value=date.today())
        
        # Get sales for selected date
        daily_sales = manager.get_daily_sales(selected_date)
        
        if daily_sales:
            # Calculate summary metrics with ALWAYS ACCURATE profit calculations
            total_sales = len(daily_sales)
            total_revenue = sum(sale['totalPaid'] for sale in daily_sales)
            
            # ALWAYS recalculate profit accurately (don't trust stored values)
            total_profit = 0
            total_cost = 0
            
            for sale in daily_sales:
                # ALWAYS recalculate - don't trust stored profit values
                sale_cost = 0
                for item in sale['cart']:
                    # Get item cost
                    item_purchase_price = item.get('purchasePrice', 0)
                    sale_cost += item_purchase_price * item['quantity']
                
                # ACCURATE profit = Amount received - Cost
                sale_profit = sale['totalPaid'] - sale_cost
                total_profit += sale_profit
                total_cost += sale_cost
            
            total_items_sold = sum(len(sale['cart']) for sale in daily_sales)
            profit_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0
            
            # Display enhanced metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Sales", total_sales)
            with col2:
                st.metric("Total Revenue", f"₹{total_revenue:.2f}")
            with col3:
                st.metric("Total Profit", f"₹{total_profit:.2f}", f"{profit_margin:.1f}% margin")
            with col4:
                st.metric("Items Sold", total_items_sold)
            
            # Additional profit insights
            col1, col2, col3 = st.columns(3)
            with col1:
                avg_profit_per_sale = total_profit / total_sales if total_sales > 0 else 0
                st.metric("Avg Profit/Sale", f"₹{avg_profit_per_sale:.2f}")
            with col2:
                avg_revenue_per_sale = total_revenue / total_sales if total_sales > 0 else 0
                st.metric("Avg Revenue/Sale", f"₹{avg_revenue_per_sale:.2f}")
            with col3:
                st.metric("Total Cost", f"₹{total_cost:.2f}")
            
            # Show success message for accurate calculation
            st.success(f"✅ Profit Accurately Calculated: ₹{total_profit:.2f}")
            
            # Sales details with accurate profit information
            st.markdown('<h3 class="section-header">Sales Details</h3>', unsafe_allow_html=True)
            
            for sale in daily_sales:
                # ALWAYS recalculate profit accurately
                sale_cost = sum(item.get('purchasePrice', 0) * item['quantity'] for item in sale['cart'])
                sale_profit = sale['totalPaid'] - sale_cost
                
                profit_margin_sale = (sale_profit / sale['totalPaid'] * 100) if sale['totalPaid'] > 0 else 0
                
                with st.expander(f"Receipt {sale['saleID']} - {sale['customerName']} - ₹{sale['totalPaid']:.2f} (Profit: ₹{sale_profit:.2f})"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Customer:** {sale['customerName']}")
                        st.write(f"**Email:** {sale['customerEmail']}")
                        st.write(f"**Phone:** {sale['customerPhone']}")
                    with col2:
                        st.write(f"**Time:** {sale['createdAt'].strftime('%I:%M %p')}")
                        st.write(f"**Total Paid:** ₹{sale['totalPaid']:.2f}")
                        st.write(f"**Profit:** ₹{sale_profit:.2f} ({profit_margin_sale:.1f}%)")
                        st.write(f"**Discount:** ₹{sale.get('discount', 0):.2f}")
                    
                    st.write("**Items:**")
                    for item in sale['cart']:
                        item_cost = item.get('purchasePrice', 0) * item['quantity']
                        
                        # Calculate accurate proportional profit for this item
                        if sale.get('subtotal', 0) > 0:
                            item_revenue_share = item['total'] / sale.get('subtotal', item['total'])
                            item_profit = sale_profit * item_revenue_share
                        else:
                            item_profit = 0
                        
                        st.write(f"• {item['itemName']} x{item['quantity']} @ ₹{item['salePrice']:.2f} = ₹{item['total']:.2f} (Cost: ₹{item_cost:.2f}, Profit: ₹{item_profit:.2f})")
            
            # Download report
            if st.button("📥 Download Detailed Excel Report with Accurate Profit Analysis"):
                excel_data = manager.generate_daily_report(selected_date)
                if excel_data:
                    st.download_button(
                        label="📥 Download Accurate Profit Report",
                        data=excel_data,
                        file_name=f"Daily_Sales_Accurate_Profit_Report_{selected_date.strftime('%Y-%m-%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
        else:
            st.info(f"No sales found for {selected_date.strftime('%B %d, %Y')}")

if __name__ == "__main__":
    main()
