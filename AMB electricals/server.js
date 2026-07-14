const express = require('express');
const cors = require('cors');
const axios = require('axios');
const dotenv = require('dotenv');
const path = require('path');
const fs = require('fs');

dotenv.config();

const app = express();
const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(express.static(path.join(__dirname)));

const receiptsDir = path.join(__dirname, 'receipts');
if (!fs.existsSync(receiptsDir)) fs.mkdirSync(receiptsDir);

const payments = [];

function generateReceiptFile(payment) {
  const receiptPath = path.join(receiptsDir, `${payment.id}.html`);
  const receiptHtml = `<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Payment Receipt</title>
    <style>
      body { font-family: Arial, sans-serif; padding: 24px; color: #10253f; }
      .card { border: 1px solid #ddd; border-radius: 12px; padding: 24px; max-width: 700px; margin: auto; }
      .header { display:flex; justify-content:space-between; align-items:center; }
      .muted { color: #666; }
      table { width:100%; border-collapse:collapse; margin-top:16px; }
      th, td { text-align:left; padding:10px; border-bottom:1px solid #eee; }
    </style>
  </head>
  <body>
    <div class="card">
      <div class="header">
        <div>
          <h2>AMB Electricals & Services</h2>
          <p class="muted">Official Payment Receipt</p>
        </div>
        <div><strong>Status:</strong> PAID</div>
      </div>
      <table>
        <tr><th>Receipt ID</th><td>${payment.id}</td></tr>
        <tr><th>Client Phone</th><td>${payment.phone}</td></tr>
        <tr><th>Amount</th><td>KES ${payment.amount}</td></tr>
        <tr><th>Reference</th><td>${payment.reference}</td></tr>
        <tr><th>Date</th><td>${new Date(payment.createdAt).toLocaleString()}</td></tr>
      </table>
      <p class="muted">This receipt confirms payment received for services rendered by AMB Electricals & Services.</p>
    </div>
  </body>
</html>`;
  fs.writeFileSync(receiptPath, receiptHtml);
  return receiptPath;
}

app.post('/api/mpesa/initiate', async (req, res) => {
  try {
    const { phone, amount, reference } = req.body;

    if (!phone || !amount) {
      return res.status(400).json({ success: false, message: 'Phone number and amount are required.' });
    }

    const payment = {
      id: `PAY-${Date.now()}`,
      phone,
      amount: Number(amount),
      reference: reference || `AMB-${Date.now()}`,
      createdAt: new Date().toISOString(),
      status: 'PENDING'
    };

    payments.push(payment);

    const receiptPath = generateReceiptFile(payment);
    payment.receiptPath = receiptPath;

    const response = {
      success: true,
      payment,
      receiptUrl: `/receipts/${path.basename(receiptPath)}`,
      message: 'Payment request received. Please complete the payment on your phone and the receipt will be generated after confirmation.'
    };

    res.json(response);
  } catch (error) {
    res.status(500).json({ success: false, message: 'Payment request failed.', error: error.message });
  }
});

app.post('/api/mpesa/callback', (req, res) => {
  const body = req.body;
  const payment = payments.find((item) => item.reference === body?.ReferenceCode || item.reference === body?.CheckoutRequestID);
  if (payment) {
    payment.status = 'PAID';
    payment.mpesaReceipt = body?.MpesaReceiptNumber || 'N/A';
    payment.updatedAt = new Date().toISOString();
    generateReceiptFile(payment);
  }
  res.json({ success: true, message: 'Callback received.' });
});

app.get('/api/payments/:id/receipt', (req, res) => {
  const payment = payments.find((item) => item.id === req.params.id);
  if (!payment) return res.status(404).json({ success: false, message: 'Payment not found.' });
  const filePath = path.join(receiptsDir, `${payment.id}.html`);
  if (!fs.existsSync(filePath)) return res.status(404).json({ success: false, message: 'Receipt not found.' });
  res.sendFile(filePath);
});

app.get('/api/payments', (req, res) => {
  res.json(payments);
});

app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'index.html'));
});

app.listen(PORT, () => {
  console.log(`Server running on http://127.0.0.1:${PORT}`);
});
