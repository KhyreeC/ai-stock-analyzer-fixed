from flask import Flask, request, jsonify
from flask_cors import CORS
import stripe

app = Flask(__name__)

# Enable CORS for all routes and all origins
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

# Stripe configuration
stripe.api_key = 'sk_test_51LtyNEK3nmVF6uBR92XZS1MIjMSZGVoMm57whwOTZ7BUv3vZkepWhqVO4q8UmIUZVDpSb6OSXQup6VgtQLXyMMFb00mthoNrYg'

PRICE_IDS = {
    'pro': 'price_1SzS0PK3nmVF6uBRY0yaKCcf',
    'premium': 'price_1SzS04K3nmVF6uBRqCupe2z9'
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
    print("=" * 60)
    print("🚀 chart.py Payment Server")
    print("=" * 60)
    print(f"📍 Server: http://localhost:5000")
    print(f"✅ CORS: Enabled for all origins")
    print(f"🔑 Stripe: {'TEST mode' if stripe.api_key.startswith('sk_test_') else 'LIVE mode'}")
    print("=" * 60)
    print("\n💡 Test: curl http://localhost:5001/health\n")
    
    app.run(host='0.0.0.0', port=5001, debug=True)