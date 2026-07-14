from flask import Flask, request, jsonify, send_file
from pathlib import Path
from datetime import datetime
import base64
import os
import requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.static_folder = '.'


@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response


BASE_DIR = Path(__file__).resolve().parent
RECEIPTS_DIR = BASE_DIR / 'receipts'
RECEIPTS_DIR.mkdir(exist_ok=True)

payments = []
MPESA_ENV = os.getenv('MPESA_ENV', 'sandbox').strip().lower()
MPESA_BASE_URL = 'https://sandbox.safaricom.co.ke' if MPESA_ENV == 'sandbox' else 'https://api.safaricom.co.ke'
MPESA_CONSUMER_KEY = os.getenv('MPESA_CONSUMER_KEY', '').strip()
MPESA_CONSUMER_SECRET = os.getenv('MPESA_CONSUMER_SECRET', '').strip()
MPESA_SHORTCODE = os.getenv('MPESA_SHORTCODE', '').strip()
MPESA_PASSKEY = os.getenv('MPESA_PASSKEY', '').strip()
MPESA_CALLBACK_URL = os.getenv('MPESA_CALLBACK_URL', '').strip()
MPESA_ACCOUNT_REFERENCE = os.getenv('MPESA_ACCOUNT_REFERENCE', 'AMB Electricals & Services').strip()
MPESA_TRANSACTION_DESC = os.getenv('MPESA_TRANSACTION_DESC', 'Payment for services').strip()


def get_mpesa_access_token():
    if not MPESA_CONSUMER_KEY or not MPESA_CONSUMER_SECRET:
        raise RuntimeError('Daraja consumer key/secret are not configured.')
    response = requests.get(
        f'{MPESA_BASE_URL}/oauth/v1/generate?grant_type=client_credentials',
        auth=(MPESA_CONSUMER_KEY, MPESA_CONSUMER_SECRET),
        timeout=30,
    )
    response.raise_for_status()
    return response.json()['access_token']


def send_stk_push(payment):
    if not MPESA_SHORTCODE or not MPESA_PASSKEY:
        raise RuntimeError('M-Pesa shortcode/passkey are not configured.')

    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    password = base64.b64encode(f'{MPESA_SHORTCODE}{MPESA_PASSKEY}{timestamp}'.encode()).decode()
    access_token = get_mpesa_access_token()

    payload = {
        'BusinessShortCode': MPESA_SHORTCODE,
        'Password': password,
        'Timestamp': timestamp,
        'TransactionType': 'CustomerPayBillOnline',
        'Amount': int(payment['amount']),
        'PartyA': payment['phone'],
        'PartyB': MPESA_SHORTCODE,
        'PhoneNumber': payment['phone'],
        'CallBackURL': MPESA_CALLBACK_URL or 'http://127.0.0.1:3000/api/mpesa/callback',
        'AccountReference': MPESA_ACCOUNT_REFERENCE,
        'TransactionDesc': MPESA_TRANSACTION_DESC,
    }

    response = requests.post(
        f'{MPESA_BASE_URL}/mpesa/stkpush/v1/processrequest',
        json=payload,
        headers={'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def generate_receipt(payment):
    receipt_path = RECEIPTS_DIR / f"{payment['id']}.html"
    html = f'''<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Payment Receipt</title>
    <style>
      body {{ font-family: Arial, sans-serif; padding: 24px; color: #10253f; }}
      .card {{ border: 1px solid #ddd; border-radius: 12px; padding: 24px; max-width: 700px; margin: auto; }}
      table {{ width: 100%; border-collapse: collapse; margin-top: 16px; }}
      th, td {{ text-align: left; padding: 10px; border-bottom: 1px solid #eee; }}
    </style>
  </head>
  <body>
    <div class="card">
      <h2>AMB Electricals & Services</h2>
      <p>Official Payment Receipt</p>
      <table>
        <tr><th>Receipt ID</th><td>{payment['id']}</td></tr>
        <tr><th>Client Phone</th><td>{payment['phone']}</td></tr>
        <tr><th>Amount</th><td>KES {payment['amount']}</td></tr>
        <tr><th>Status</th><td>{payment['status']}</td></tr>
        <tr><th>Date</th><td>{payment['created_at']}</td></tr>
      </table>
      <p>This receipt confirms payment received for services rendered by AMB Electricals & Services.</p>
    </div>
  </body>
</html>'''
    receipt_path.write_text(html, encoding='utf-8')
    return receipt_path


@app.route('/api/mpesa/initiate', methods=['POST'])
def initiate_payment():
    data = request.get_json(silent=True) or {}
    phone = data.get('phone', '').strip()
    amount = data.get('amount')

    if not phone or not amount:
        return jsonify({'success': False, 'message': 'Phone number and amount are required.'}), 400

    payment = {
        'id': f"PAY-{int(datetime.now().timestamp())}",
        'phone': phone,
        'amount': float(amount),
        'status': 'PENDING',
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'reference': f"AMB-{int(datetime.now().timestamp())}"
    }
    payments.append(payment)
    generate_receipt(payment)

    try:
        stk_response = send_stk_push(payment)
        payment['status'] = 'INITIATED'
        payment['checkout_request_id'] = stk_response.get('CheckoutRequestID')
        payment['merchant_request_id'] = stk_response.get('MerchantRequestID')
        payment['stk_message'] = stk_response.get('CustomerMessage', 'STK push initiated.')
        generate_receipt(payment)
        return jsonify({
            'success': True,
            'message': 'Payment request sent to M-Pesa. Complete the prompt on your phone to pay.',
            'receiptUrl': f"/api/payments/{payment['id']}/receipt",
            'payment': payment
        })
    except Exception as exc:
        payment['status'] = 'PENDING'
        payment['error'] = str(exc)
        generate_receipt(payment)
        return jsonify({
            'success': True,
            'message': 'Payment request recorded. Add your Daraja credentials to process live M-Pesa payments automatically.',
            'receiptUrl': f"/api/payments/{payment['id']}/receipt",
            'payment': payment
        })


@app.route('/api/payments/<payment_id>/receipt')
def get_receipt(payment_id):
    receipt_path = RECEIPTS_DIR / f'{payment_id}.html'
    if not receipt_path.exists():
        return jsonify({'success': False, 'message': 'Receipt not found.'}), 404
    return send_file(receipt_path, mimetype='text/html', as_attachment=True, download_name=f'{payment_id}.html')


@app.route('/api/mpesa/callback', methods=['POST'])
def mpesa_callback():
    body = request.get_json(silent=True) or {}
    payment = next((item for item in payments if item.get('reference') == body.get('ReferenceCode') or item.get('checkout_request_id') == body.get('CheckoutRequestID')), None)
    if payment:
        payment['status'] = 'PAID'
        payment['mpesa_receipt'] = body.get('MpesaReceiptNumber', 'N/A')
        payment['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        generate_receipt(payment)
    return jsonify({'success': True, 'message': 'Callback received.'})


@app.route('/api/payments')
def list_payments():
    return jsonify(payments)


@app.route('/')
def index():
    return app.send_static_file('index.html')


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=3000, debug=True)
