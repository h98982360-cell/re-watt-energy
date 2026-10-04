# API Reference - Re-Watt Energy

Complete API endpoint documentation for the Re-Watt Energy marketplace.

**Base URL**: `https://<backend-url>` (e.g., `http://localhost:8000` for local dev)

**Authentication**: All endpoints except `/health` and `/api/auth/register`/`/api/auth/login` require `Authorization: Bearer <token>` header.

---

## Table of Contents

1. [Health](#health)
2. [Authentication](#authentication)
3. [Catalog](#catalog)
4. [Marketplace](#marketplace)
   - [Listings](#listings)
   - [Requirements](#requirements)
   - [Matches](#matches)
   - [Transactions](#transactions)
5. [Admin](#admin)

---

## Health

### GET /health
Check API status.

**Status**: Public  
**Response**: 200 OK
```json
{
  "status": "ok"
}
```

---

## Authentication

### POST /api/auth/register
Register a new user (supplier, buyer, or admin).

**Status**: Public  
**Request**:
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123",
  "full_name": "John Doe",
  "role": "supplier|buyer|admin",
  "supplier_org": "Farm Name (supplier only)",
  "supplier_county": "Kiambu (supplier only)",
  "buyer_county": "Nairobi (buyer only)"
}
```

**Response**: 201 Created
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "full_name": "John Doe",
  "role": "supplier",
  "status": "pending",
  "profile": {
    "verification_status": "unverified"
  }
}
```

**Errors**:
- `400 Bad Request` - Email already exists, invalid password, or missing required fields
- `422 Unprocessable Entity` - Invalid email format

---

### POST /api/auth/login
Log in and get access token.

**Status**: Public  
**Request**:
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123"
}
```

**Response**: 200 OK
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "full_name": "John Doe",
    "role": "supplier"
  }
}
```

**Errors**:
- `401 Unauthorized` - Invalid email or password
- `404 Not Found` - User does not exist

---

### GET /api/profile
Get current logged-in user profile.

**Status**: Authenticated (all users)  
**Response**: 200 OK
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "full_name": "John Doe",
  "role": "supplier",
  "status": "active",
  "profile": {
    "verification_status": "verified",
    "supplier_org": "Farm Name"
  }
}
```

---

## Catalog

### GET /api/catalog
Retrieve material catalog (categories and materials).

**Status**: Public  
**Response**: 200 OK
```json
[
  {
    "category_id": "biomass",
    "category_name": "Biomass",
    "materials": [
      {
        "id": "maize-cobs",
        "name": "Maize Cobs",
        "slug": "maize-cobs",
        "category": "biomass",
        "unit": "kg",
        "description": "Dried maize cobs suitable for briquetting"
      },
      {
        "id": "maize-stover",
        "name": "Maize Stover",
        "slug": "maize-stover",
        "category": "biomass",
        "unit": "kg",
        "description": "Dried maize stalks and leaves"
      }
    ]
  }
]
```

---

## Marketplace

### Listings

#### POST /api/listings
Create a new supply listing (suppliers only).

**Status**: Authenticated (supplier, verified only)  
**Request**:
```json
{
  "material_id": "maize-cobs",
  "quantity_declared": 500,
  "unit_declared": "kg",
  "condition": "dry",
  "county": "Kiambu",
  "availability_date": "2024-02-01",
  "price_per_unit": 15.50,
  "description": "High-quality maize cobs"
}
```

**Response**: 201 Created
```json
{
  "id": "uuid",
  "supplier_id": "uuid",
  "material_id": "maize-cobs",
  "quantity_declared": 500,
  "quantity_base": 500,
  "unit_declared": "kg",
  "base_unit": "kg",
  "condition": "dry",
  "county": "Kiambu",
  "status": "active",
  "created_at": "2024-01-15T10:30:00Z"
}
```

**Errors**:
- `401 Unauthorized` - Not authenticated
- `403 Forbidden` - Not a supplier or not verified
- `400 Bad Request` - Invalid material or quantity

---

#### GET /api/listings
Browse active supply listings.

**Status**: Public  
**Query Parameters**:
- `material_id` (optional): Filter by material
- `county` (optional): Filter by county
- `condition` (optional): Filter by condition
- `skip` (default: 0): Pagination offset
- `limit` (default: 20): Results per page

**Response**: 200 OK
```json
[
  {
    "id": "uuid",
    "supplier_id": "uuid",
    "supplier_name": "John Doe",
    "material_id": "maize-cobs",
    "quantity_declared": 500,
    "quantity_base": 500,
    "base_unit": "kg",
    "condition": "dry",
    "county": "Kiambu",
    "price_per_unit": 15.50,
    "status": "active"
  }
]
```

---

### Requirements

#### POST /api/requirements
Post a buyer requirement (buyers only).

**Status**: Authenticated (buyer, verified only)  
**Request**:
```json
{
  "material_id": "maize-cobs",
  "quantity_needed_base": 1000,
  "unit_base": "kg",
  "county_preferred": "Kiambu",
  "price_target": 16.00,
  "description": "Need for briquette production"
}
```

**Response**: 201 Created
```json
{
  "id": "uuid",
  "buyer_id": "uuid",
  "material_id": "maize-cobs",
  "quantity_needed_base": 1000,
  "unit_base": "kg",
  "county_preferred": "Kiambu",
  "status": "open",
  "created_at": "2024-01-15T11:00:00Z"
}
```

---

#### GET /api/requirements
Get buyer's own requirements.

**Status**: Authenticated (buyers)  
**Response**: 200 OK
```json
[
  {
    "id": "uuid",
    "buyer_id": "uuid",
    "material_id": "maize-cobs",
    "quantity_needed_base": 1000,
    "unit_base": "kg",
    "county_preferred": "Kiambu",
    "status": "open"
  }
]
```

---

### Matches

#### GET /api/matches
Get aggregated matches for buyer's requirements.

**Status**: Authenticated (buyers)  
**Response**: 200 OK
```json
[
  {
    "id": "uuid",
    "requirement_id": "uuid",
    "material_id": "maize-cobs",
    "status": "pending_supplier_acceptance",
    "matched_quantity": 500,
    "matched_quantity_base": 500,
    "base_unit": "kg",
    "total_price": 7750.00,
    "price_per_unit": 15.50,
    "aggregated_from": 1,
    "items": [
      {
        "id": "uuid",
        "listing_id": "uuid",
        "supplier_id": "uuid",
        "supplier_name": "John Doe",
        "allocated_quantity": 500,
        "allocated_quantity_base": 500,
        "county": "Kiambu",
        "condition": "dry"
      }
    ]
  }
]
```

---

#### PATCH /api/marketplace/matches/{match_id}/accept
Supplier accepts a match (supplier only).

**Status**: Authenticated (supplier)  
**Request**: (empty body)

**Response**: 200 OK
```json
{
  "id": "uuid",
  "status": "supplier_accepted",
  "transaction_ids": ["uuid"]
}
```

---

### Transactions

#### GET /api/marketplace/transactions
Get user's transactions (supplier or buyer).

**Status**: Authenticated  
**Query Parameters**:
- `role` (optional): Filter by role (supplier, buyer)
- `status` (optional): Filter by status (pending, handover, receipt, payment, completed)

**Response**: 200 OK
```json
[
  {
    "id": "uuid",
    "match_id": "uuid",
    "supplier_id": "uuid",
    "supplier_name": "John Doe",
    "buyer_id": "uuid",
    "buyer_name": "Buyer Corp",
    "material_id": "maize-cobs",
    "quantity_allocated": 500,
    "quantity_base": 500,
    "base_unit": "kg",
    "price_per_unit": 15.50,
    "total_price": 7750.00,
    "status": "handover",
    "created_at": "2024-01-15T12:00:00Z"
  }
]
```

---

#### PATCH /api/marketplace/transactions/{transaction_id}/confirm-receipt
Buyer confirms receipt and quantity (buyer only).

**Status**: Authenticated (buyer)  
**Request**:
```json
{
  "quantity_received": 480,
  "notes": "10 kg moisture loss during transport"
}
```

**Response**: 200 OK
```json
{
  "id": "uuid",
  "status": "receipt",
  "quantity_received": 480,
  "variance": -20
}
```

---

#### PATCH /api/marketplace/transactions/{transaction_id}/record-payment
Record payment (either party).

**Status**: Authenticated  
**Request**:
```json
{
  "payment_reference": "M-PESA-ABC123XYZ",
  "amount_paid": 7750.00,
  "payer_role": "buyer|supplier"
}
```

**Response**: 200 OK
```json
{
  "id": "uuid",
  "status": "payment",
  "payment_reference": "M-PESA-ABC123XYZ",
  "amount_paid": 7750.00
}
```

---

#### PATCH /api/marketplace/transactions/{transaction_id}/confirm-completed
Confirm transaction complete (either party).

**Status**: Authenticated  
**Request**: (empty body)

**Response**: 200 OK
```json
{
  "id": "uuid",
  "status": "completed",
  "completed_at": "2024-01-16T14:30:00Z"
}
```

---

## Admin

### GET /api/admin/verifications/pending
Get list of users pending verification.

**Status**: Authenticated (admin only)  
**Response**: 200 OK
```json
[
  {
    "user_id": "uuid",
    "email": "supplier@example.com",
    "full_name": "John Doe",
    "role": "supplier",
    "org_name": "Farm Name",
    "created_at": "2024-01-15T09:00:00Z"
  }
]
```

---

### PATCH /api/admin/verifications/{user_id}
Verify or reject a user.

**Status**: Authenticated (admin only)  
**Request**:
```json
{
  "decision": "verified|rejected",
  "notes": "Verification complete"
}
```

**Response**: 200 OK
```json
{
  "user_id": "uuid",
  "status": "active",
  "verification_status": "verified",
  "updated_at": "2024-01-15T15:30:00Z"
}
```

---

## Error Responses

All endpoints return standardized error responses:

### 400 Bad Request
```json
{
  "detail": "Invalid request: [specific error message]"
}
```

### 401 Unauthorized
```json
{
  "detail": "Not authenticated"
}
```

### 403 Forbidden
```json
{
  "detail": "Not authorized to perform this action"
}
```

### 404 Not Found
```json
{
  "detail": "Resource not found"
}
```

### 422 Unprocessable Entity
```json
{
  "detail": [
    {
      "loc": ["body", "field_name"],
      "msg": "error message",
      "type": "value_error"
    }
  ]
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

---

## Authentication Token

Include in all authenticated requests:
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

Token obtained from `/api/auth/login` response. Default expiry: 24 hours.

---

## Rate Limiting

No rate limiting in MVP. Will be added at gateway level in production.

---

## CORS

Frontend origin must be in `CORS_ORIGINS` environment variable.

**Development**: `http://localhost:5173`  
**Production**: `https://rewatt-marketplace.onrender.com`

---

## Pagination

List endpoints support:
- `skip`: Number of items to skip (default: 0)
- `limit`: Number of items to return (default: 20, max: 100)

**Example**:
```
GET /api/listings?skip=20&limit=10
```

---

## Example Workflows

### Supplier Listing Flow
```
1. POST /api/auth/register (role: supplier)
2. Admin PATCH /api/admin/verifications/{user_id} (verified)
3. GET /api/catalog (get material_id)
4. POST /api/listings (create supply)
5. GET /api/marketplace/matches (wait for buyer)
6. PATCH /api/marketplace/matches/{match_id}/accept
7. GET /api/marketplace/transactions
8. PATCH /api/marketplace/transactions/{id}/record-payment
9. PATCH /api/marketplace/transactions/{id}/confirm-completed
```

### Buyer Procurement Flow
```
1. POST /api/auth/register (role: buyer)
2. Admin PATCH /api/admin/verifications/{user_id} (verified)
3. GET /api/listings (browse supply)
4. POST /api/requirements (post need)
5. GET /api/matches (get aggregated matches)
6. PATCH /api/marketplace/transactions/{id}/confirm-receipt
7. PATCH /api/marketplace/transactions/{id}/record-payment
8. PATCH /api/marketplace/transactions/{id}/confirm-completed
```

---

## Testing

### Swagger UI (Interactive)
Visit `http://localhost:8000/docs` (local) or `https://<backend-url>/docs` (production)

### cURL Examples
See `QUICK_START.md` for complete cURL workflow examples.

---

## Support

For issues or questions:
1. Check `http://localhost:8000/docs` (Swagger UI) for live schema
2. Review `QUICK_START.md` for workflow examples
3. Open a GitHub issue with `[api]` prefix
