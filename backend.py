from flask import Flask, request, jsonify
from flask_cors import CORS
import stripe
import os
from dotenv import load_dotenv

app = Flask(__name__)

# Enable CORS for all routes and all origins
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

# Load environment variables from .env file
load_dotenv()


# Stripe configuration
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

PRICE_IDS = {
    'starter': os.getenv('STARTER_PRICE_ID'),
    'pro': os.getenv('PRO_PRICE_ID'),
    'premium': os.getenv('PREMIUM_PRICE_ID'),
}

# In-memory customer storage
customers = {}

@app.route('/create-subscription', methods=['POST', 'OPTIONS'])
def create_subscription():
    """Create a Stripe subscription"""
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        data = request.json
        payment_method_id = data['paymentMethodId']
        price_id = data['priceId']
        email = data['email']

        print(f"📥 Received request:")
        print(f"  Email: {email}")
        print(f"  Price ID: {price_id}")
        print(f"  Payment Method: {payment_method_id}")
        
        # Create or retrieve customer
        if email in customers:
            customer = customers[email]
            print(f"♻️  Using existing customer: {customer.id}")
        else:
            customer = stripe.Customer.create(
                email=email,
                payment_method=payment_method_id,
                invoice_settings={
                    'default_payment_method': payment_method_id,
                },
            )
            customers[email] = customer
            print(f"✅ Created new customer: {customer.id}")
        
        # Create subscription
        subscription = stripe.Subscription.create(
            customer=customer.id,
            items=[{'price': price_id}],
            expand=['latest_invoice.payment_intent'],
        )
        
        print(f"🎉 Subscription created: {subscription.id}")
        print(f"💰 Status: {subscription.status}")
        
        return jsonify({
            'subscriptionId': subscription.id,
            'status': subscription.status
        })
    
    except stripe.error.CardError as e:
        print(f"❌ Card error: {e.user_message}")
        return jsonify({'error': str(e.user_message)}), 400
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'stripe_connected': True})


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5050))
    print("=" * 60)
    print("🚀 chart.py Payment Server")
    print("=" * 60)
    print(f"📍 Server: http://localhost:{port}")
    print(f"✅ CORS: Enabled for all origins")
    if stripe.api_key:
        mode = "TEST mode" if stripe.api_key.startswith("sk_test_") else "LIVE mode"
    else:
        mode = "NO KEY LOADED"
    print(f"🔑 Stripe: {mode}")
    print("=" * 60)
    print(f"\n💡 Test: curl http://localhost:{port}/health\n")

    app.run(host='0.0.0.0', port=port, debug=True)
