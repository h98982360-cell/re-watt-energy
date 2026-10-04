# Quick Start Guide - Re-Watt Energy

Get the Re-Watt Energy marketplace running locally in 5 minutes.

---

## Prerequisites

- Python 3.12+
- Node.js 18+
- Git

---

## Option 1: Backend Only (API Testing)

```bash
# Navigate to backend
cd backend

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env

# Run backend
python -m uvicorn app.main:app --reload

# 🚀 API running at http://localhost:8000
# 📚 Docs at http://localhost:8000/docs
```

**Test health:**
```bash
curl http://localhost:8000/health
```

---

## Option 2: Frontend Only (UI Development)

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Run dev server
npm run dev

# 🚀 Frontend running at http://localhost:5173
```

---

## Option 3: Full Stack (Recommended for Testing)

### Terminal 1: Backend

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 0.0.0.0
```

### Terminal 2: Frontend

```bash
cd frontend
npm install
npm run dev
```

### Terminal 3: Test

```bash
cd backend
pytest tests/test_marketplace_flow.py -v
```

---

## Quick Demo Workflow

### 1. Register Supplier

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "supplier@example.com",
    "password": "Test123!",
    "full_name": "Farmer John",
    "role": "supplier",
    "supplier_org": "John Farm",
    "supplier_county": "Kiambu"
  }'
```

### 2. Register Buyer

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "buyer@example.com",
    "password": "Test123!",
    "full_name": "Buyer Corp",
    "role": "buyer",
    "buyer_county": "Nairobi"
  }'
```

### 3. Admin Verification

Login as admin (default from env):
- Email: `admin@example.com`
- Password: (check `.env` ADMIN_PASSWORD)

Then in Swagger UI (`http://localhost:8000/docs`):
1. Click **Authorize** → paste admin token
2. Go to PATCH `/api/admin/verifications/{user_id}`
3. Enter supplier user_id, decision: `"verified"`

### 4. Create Listing (as Supplier)

Get supplier token:
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "supplier@example.com",
    "password": "Test123!"
  }'
```

Create listing:
```bash
curl -X POST http://localhost:8000/api/listings \
  -H "Authorization: Bearer <SUPPLIER_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "material_id": "maize-cobs",
    "quantity_declared": 500,
    "unit_declared": "kg",
    "condition": "dry",
    "county": "Kiambu",
    "description": "Quality maize cobs"
  }'
```

### 5. Post Requirement (as Buyer)

Get buyer token, then:
```bash
curl -X POST http://localhost:8000/api/requirements \
  -H "Authorization: Bearer <BUYER_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "material_id": "maize-cobs",
    "quantity_needed_base": 800,
    "unit_base": "kg",
    "county_preferred": "Kiambu"
  }'
```

### 6. Browse Matches (as Buyer)

```bash
curl http://localhost:8000/api/matches \
  -H "Authorization: Bearer <BUYER_TOKEN>"
```

You'll see aggregated listing(s) ready for acceptance.

---

## Environment Variables

### Backend (.env)

```
DATABASE_URL=sqlite:///./rewatt.db
SECRET_KEY=dev-secret-key-change-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=AdminPassword123
ADMIN_NAME=Admin User
PLATFORM_FEE_PERCENT=5.0
EXPOSE_VERIFICATION_CODES=true
CORS_ORIGINS=["http://localhost:5173", "http://localhost:3000"]
```

### Frontend (.env)

```
VITE_API_URL=http://localhost:8000
VITE_API_TIMEOUT=30000
```

---

## Running Tests

```bash
cd backend
pip install pytest
pytest tests/test_marketplace_flow.py -v
```

**Expected output:**
```
test_health_catalog_and_registration PASSED
test_unverified_supplier_cannot_publish PASSED
test_aggregated_match_supplier_acceptance_and_transaction PASSED
```

---

## Project Structure

```
re-watt-energy/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app
│   │   ├── config.py            # Settings
│   │   ├── database.py          # SQLAlchemy setup
│   │   ├── security.py          # Auth & encryption
│   │   ├── models/              # ORM models
│   │   │   ├── user.py
│   │   │   └── marketplace.py
│   │   ├── services/            # Business logic
│   │   │   ├── matching.py
│   │   │   └── catalog.py
│   │   └── api/routes/          # API endpoints
│   │       ├── auth.py
│   │       ├── marketplace.py
│   │       └── admin.py
│   ├── tests/
│   │   └── test_marketplace_flow.py
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx              # Main React app
│   │   ├── api.ts               # HTTP client
│   │   ├── main.tsx             # Entry point
│   │   └── styles.css           # Styles
│   ├── index.html
│   ├── package.json
│   └── tsconfig.json
│
├── render.yaml                  # Deployment config
├── README.md                    # Full spec
└── DEPLOYMENT.md                # Production guide
```

---

## Common Commands

```bash
# Backend
cd backend
pip install -r requirements.txt          # Install deps
python -m uvicorn app.main:app --reload # Run
pytest tests/ -v                         # Test
black app/ tests/                        # Format (install: pip install black)
mypy app/                                # Type check (install: pip install mypy)

# Frontend
cd frontend
npm install                              # Install deps
npm run dev                              # Run dev server
npm run build                            # Build for production
npm run preview                          # Preview production build
npm run type-check                       # TypeScript check
```

---

## Troubleshooting

### Backend won't start
```bash
# Check Python version
python --version  # Should be 3.12+

# Reinstall requirements
pip install --upgrade pip
pip install -r backend/requirements.txt

# Check port
lsof -i :8000  # Port 8000 in use?
```

### Frontend build fails
```bash
# Clear cache
rm -rf node_modules package-lock.json
npm install
npm run build
```

### Tests fail
```bash
# Reinstall test dependencies
pip install pytest httpx

# Run with verbose output
pytest tests/test_marketplace_flow.py -vv
```

### SQLite locked error
```bash
# Delete stale database
rm backend/rewatt.db
# Tests will recreate it
pytest tests/test_marketplace_flow.py -v
```

---

## Next Steps

1. ✅ Run locally and explore the UI
2. ✅ Try the API in Swagger UI (`http://localhost:8000/docs`)
3. ✅ Walk through end-to-end workflow (register → verify → list → match → transact)
4. ✅ Review code in `backend/app/api/routes/marketplace.py` (core workflow)
5. ✅ Deploy to Render (see `DEPLOYMENT.md`)

---

## Support

- **API Docs**: `http://localhost:8000/docs` (Swagger UI)
- **GitHub Issues**: Create an issue with `[local]` prefix
- **Code Walkthrough**: See inline comments in `app/api/routes/marketplace.py`

---

**Happy hacking! 🚀**
