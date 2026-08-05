# LedgerMate

A simple, web-based financial management app for small businesses. LedgerMate helps small business owners and traders track income and expenses, manage inventory, generate financial reports, and automatically reconcile Paystack payments — all in one place.

## Problem

Small business owners, especially informal traders and SMEs in Kenya, often rely on manual bookkeeping that's slow and error-prone. Most existing accounting tools are either too complex or too expensive for this market, and there's rarely a simple way to reconcile mobile-money-based payments with business records automatically.

## Features

- **Transactions** — record and categorize income and expenses
- **Inventory** — track stock items and movements (stock in/out)
- **Reports** — profit & loss, balance sheet, monthly/yearly comparisons, and liabilities tracking
- **Forecasting** — lightweight, explainable revenue forecasting using linear regression over monthly totals (no black-box ML)
- **Export** — download reports as PDF or CSV
- **Payments** — accept payments via Paystack, with automatic transaction matching through signed webhooks (no manual entry needed)

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, Flask |
| Database | PostgreSQL (production), SQLite (local dev) |
| ORM / Migrations | SQLAlchemy, Flask-Migrate (Alembic) |
| Auth | Flask-Login |
| Templates | Jinja2, HTML/CSS/JavaScript |
| Payments | Paystack API |
| Reporting | NumPy, Pandas, ReportLab (PDF), openpyxl (Excel) |
| Server | Gunicorn |
| Containerization | Docker |

## Getting Started

### Prerequisites
- Python 3.12+
- pip

### Local Setup

```bash
git clone <repo-url>
cd LedgerMate

python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env        # then fill in your own values
```

### Environment Variables

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | Yes (prod) | Flask session/CSRF signing key |
| `DATABASE_URL` | No | Postgres connection string. Falls back to local SQLite if unset |
| `PAYSTACK_SECRET_KEY` | For payments | From Paystack dashboard → Settings → API Keys |
| `PAYSTACK_PUBLIC_KEY` | For payments | From Paystack dashboard → Settings → API Keys |

### Database Setup

```bash
export FLASK_APP=run.py
flask db upgrade
```

### Run Locally

```bash
python run.py
```
App runs at `http://localhost:5000`.

### Run with Docker

```bash
docker build -t ledgermate .
docker run -p 8000:8000 \
  -e SECRET_KEY=your-secret-key \
  -e DATABASE_URL=postgresql://user:pass@host:5432/ledgermate \
  -e PAYSTACK_SECRET_KEY=sk_test_xxx \
  -e PAYSTACK_PUBLIC_KEY=pk_test_xxx \
  ledgermate
```
The container automatically applies pending database migrations on startup before starting the server.

### Paystack Webhook Setup

In your Paystack dashboard, under **Settings → API Keys & Webhooks**, set the webhook URL to:
```
https://yourdomain.com/payments/webhook
```
Every webhook is verified against its HMAC SHA512 signature before being trusted, so it can't be spoofed.

## Project Structure

```
LedgerMate/
├── app/
│   ├── controllers/     # Route blueprints (auth, transactions, reports, inventory, payments, categories)
│   ├── models/           # SQLAlchemy models
│   ├── services/         # Business logic (forecasting, export/PDF generation)
│   ├── static/            # CSS, JS, images
│   └── templates/       # Jinja2 templates
├── migrations/          # Alembic database migrations
├── config.py            # App configuration
├── run.py               # Local development entrypoint
├── index.py             # Production entrypoint (gunicorn)
├── Dockerfile
└── requirements.txt
```
