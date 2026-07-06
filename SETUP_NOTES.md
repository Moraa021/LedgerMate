# What changed & what you need to do

## 1. Logo
Your `logo.png` had **no CSS at all** applied to it, so it was rendering at its
native 515×368px size. Added `.app-header` / `.app-logo` rules in
`app/static/css/main.css` (and a slightly smaller size on very small screens
in `mobile.css`). It now sits at a normal ~32px header height.

## 2. Reports page
Rebuilt `app/templates/reports/reports.html`. The old version used Bootstrap
classes (`btn-outline-primary`, `row`, `col-md-6`, `table-bordered`, etc.)
but **Bootstrap was never actually loaded** anywhere in the app - only your
own `main.css`. That's why it looked/behaved inconsistently vs. Dashboard
and Transactions. The new version uses only your existing design system
(`.card`, `.btn`, `.form-control`) and adds tabs for:
- Summary report (same as before, just restyled)
- **Profit & Loss statement**
- **Balance Sheet**
- **AI Forecast**

> Note: `add_transaction.html` still relies on the same missing Bootstrap
> classes (`btn-check`, `form-select`, `input-group`...) - I left it alone
> since you didn't ask about it, but it's worth knowing it has the same
> underlying issue if you notice it looking off too.

## 3. Paystack - automatic transaction detection
There was actually no live Daraja/M-Pesa API integration in the codebase to
migrate away from - "M-Pesa" was just a manual payment-method label where
you typed in your own confirmation code. This is now replaced with a real,
automatic flow:

- **Dashboard → "Get Paid via Paystack"** (or `/payments/request`) lets you
  generate a payment link for a specific amount/customer.
- The customer pays on Paystack's hosted checkout (card, and M-Pesa/mobile
  money where Paystack supports it in Kenya).
- Paystack calls **`/payments/webhook`** when the payment clears, and that's
  what creates the Transaction automatically - nobody types anything in.

**You need to set these environment variables** (get them from
https://dashboard.paystack.com/#/settings/developers):
```
PAYSTACK_SECRET_KEY=sk_live_or_test_xxx
PAYSTACK_PUBLIC_KEY=pk_live_or_test_xxx
```
Then in the Paystack dashboard, under **Settings → API Keys & Webhooks**, set
your webhook URL to:
```
https://yourdomain.com/payments/webhook
```
Paystack signs every webhook with your secret key (HMAC SHA512); the handler
verifies this signature before trusting any event, so it can't be spoofed.

`requests` was added to `requirements.txt` since it's needed to call the
Paystack API - run `pip install -r requirements.txt` again.

## 4. Profit & Loss / Balance Sheet
- **P&L** groups your existing income/expense transactions by category over
  a date range into a standard Revenue / Expenses / Net Profit statement.
- **Balance Sheet** is intentionally simplified for a small business without
  full double-entry books:
  - Assets = cash on hand (cumulative income − expense) + inventory value
  - Liabilities = any loans/payables you add manually (new small form on
    the Balance Sheet tab)
  - Equity = Assets − Liabilities

## 5. Inventory management
New "Stock" tab in the bottom nav (`/inventory`). Add items with cost/price/
reorder level, then log **restocks**, **sales**, or manual **adjustments**.
Stock value feeds directly into the Balance Sheet's Assets. Low-stock items
show a banner + badge.

## 6. AI Forecasting
New tab on the Reports page. Uses a simple, explainable linear regression
over your last 12 months of income/expense totals to project the next 3-6
months, plus a couple of plain-language insights (e.g. trending up/down,
projected net). It's a trend projection, not a guarantee - said explicitly
in the UI.

## 7. Database migration
New tables (`inventory_items`, `inventory_movements`, `liabilities`,
`payment_requests`) and new columns on `transactions`
(`paystack_reference`, `paystack_status`, `payer_email`, `payer_name`).

- **Fresh/dev SQLite DB:** `db.create_all()` in `app/__init__.py` will
  create the new tables automatically, but it **won't alter the existing
  `transactions` table** to add the new columns.
- **Recommended for any existing database:** run your normal Flask-Migrate
  flow:
  ```
  flask db migrate -m "add paystack, inventory, liabilities"
  flask db upgrade
  ```
