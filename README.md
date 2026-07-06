# LedgerMate

A bookkeeping app for Kenyan micro/small businesses (Flask + SQLAlchemy),
with M-Pesa (Daraja) auto-entry, inventory management, AI-assisted cash flow
forecasting, and simplified financial statements (P&L / Balance Sheet).

## What's new in this build

| Feature | Where |
|---|---|
| M-Pesa (Daraja) auto-entry | `app/services/mpesa_service.py`, `app/controllers/mpesa_controller.py` |
| Inventory management | `app/services/inventory_service.py`, `app/controllers/inventory_controller.py`, `/inventory` page |
| Profit & Loss / Balance Sheet | `app/services/financial_statement_service.py`, new cards on the Reports page |
| Cash flow forecasting | `app/services/forecast_service.py`, "Cash Flow Forecast" card on Reports page |

New database tables: `inventory_items`, `stock_movements`, `mpesa_transactions`.
`transactions` gained two new nullable columns: `inventory_item_id`, `is_cogs`.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # then fill in real values
```

### Database migration

This project uses Flask-Migrate. Since it wasn't yet initialized:

```bash
flask db init          # only the first time, if migrations/ doesn't exist
flask db migrate -m "Add inventory, mpesa, and cogs tracking"
flask db upgrade
```

If you're only running locally on SQLite and don't mind losing existing data,
`python init_db.py` (calls `db.create_all()`) is enough for new tables — but
`db.create_all()` will **not** add the two new columns to an existing
`transactions` table, so use the migration path above for any real data.

### M-Pesa / Daraja setup

1. Create an app at [developer.safaricom.co.ke](https://developer.safaricom.co.ke)
   and grab a sandbox Consumer Key/Secret.
2. Fill in `MPESA_*` variables in `.env` (sandbox shortcode `174379` works
   out of the box for testing).
3. Expose your local server publicly so Safaricom's servers can reach it:
   ```bash
   ngrok http 5000
   ```
   Put the `https://...ngrok-free.app` URL in `MPESA_CALLBACK_BASE_URL`.
4. Two ways transactions get created automatically:
   - **STK Push** (you request payment from inside the app): call
     `POST /mpesa/stkpush` with `{ "phone_number": "2547XXXXXXXX", "amount": 500 }`.
     The customer gets a prompt on their phone; once they enter their PIN,
     Safaricom calls `/mpesa/callback/stk` and LedgerMate posts an income
     transaction automatically.
   - **C2B** (customer pays your Paybill/Till directly, unprompted): register
     your callback URLs once via `mpesa_service.register_c2b_urls()` (run it
     from `flask shell`). Tell customers to use their phone number or your
     LedgerMate account ID as the "Account Number" so the payment gets
     matched to the right business — otherwise it's credited to
     `MPESA_DEFAULT_USER_ID` if you set one (single-business mode).
5. Go to production only after Safaricom approves your go-live application;
   then set `MPESA_ENV=production` and use your real shortcode/passkey.

### Inventory

Visit `/inventory` (linked from the Profile page). Add an item with an
opening quantity/cost, then use **+ Buy** / **- Sell** to record purchases
and sales. Both automatically:
- Update the item's weighted-average unit cost
- Post a `Transaction` to the ledger (expense for purchases, income + a
  separate COGS expense for sales)

### Profit & Loss / Balance Sheet / Forecast

All three live as new cards on the **Reports** page and call:
- `GET /reports/api/profit-loss?from_date=...&to_date=...`
- `GET /reports/api/balance-sheet?as_of_date=...`
- `GET /reports/api/forecast?horizon_days=30&lookback_days=90`

**Read this before showing these to a bank or investor:** LedgerMate keeps a
single-entry, cash-basis ledger, not full double-entry books. That means:
- No accounts payable/receivable — everything's assumed settled in cash/M-Pesa.
- The Balance Sheet values inventory at *today's* weighted-average cost, so
  past-dated balance sheets are an approximation.
- Owner's Equity is a plug (Assets − Liabilities), since capital
  contributions/drawings aren't tracked separately from trading profit.

These are solid for day-to-day decisions; have an accountant review before
using them for a loan application, investor due diligence, or KRA filing.

The forecast is a linear-trend model over your last 90 days of daily
totals (falls back to a moving average with under a week of history) — it's
intentionally simple rather than a black box, since that's what generalizes
best from the transaction volumes a small business logs.

## Existing features (unchanged)

Multi-language (EN/SW) UI, transactions with categories, PDF/CSV/Excel
report export, a rule-based bookkeeping chatbot, dashboard charts.
