# FoodPulse Analytics — Charts & UI Edition

Full-stack online food delivery analytics dashboard built with React + Vite, FastAPI and MongoDB.

## Modules
- Overview dashboard with KPI cards, revenue trend, order-status distribution, restaurant ranking and business insights.
- Orders with status and restaurant-value charts, payment-method donut chart, average order value by city, search, status filters and order status updates.
- Restaurants with cuisine/rating charts and CSV export.
- Customers with city, contact coverage, order-frequency segments, city-mix donut chart and CSV export.
- Menu with category/price charts and CSV export.
- Deliveries with status distribution, average partner delivery time, delivery-time-by-distance bands, status-mix donut chart, editable delivery status and CSV export.
- Analytics with revenue and restaurant performance.
- Reports with date/status/restaurant filters and downloadable CSV orders report.
- Responsive desktop and mobile UI styling.

## Requirements
- Python 3.10+ (Python 3.12 recommended)
- Node.js 18+
- MongoDB local service or MongoDB Atlas URI

## Start backend (PowerShell)
```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```
Set `MONGODB_URI` and `MONGODB_DB` in `backend/.env` before starting. API docs: http://127.0.0.1:8000/docs

## Seed demo data
From project root:
```powershell
python database/seed_database.py
```
The seeder recreates demo collections. Back up any data you want to keep before running it.

## Start frontend (second terminal)
```powershell
cd frontend
npm install
npm run dev
```
Open the Vite URL, normally http://localhost:5173. Confirm `frontend/.env` points to `http://127.0.0.1:8000/api` if required by your setup.

Demo credentials: `admin@foodpulse.com` / `Admin@123` (as configured by the included demo seeder).

## Notes
Charts are computed from records returned by the API. For larger datasets, use the included large-dataset seeder. Charts do not generate artificial business metrics; all visualizations reflect the MongoDB records.

## Update in this version

- **Delivery status editing:** In Deliveries, use the status dropdown for each row. Changes are persisted through `PATCH /api/deliveries/{delivery_id}/status`; the related order is synchronized where the delivery's `order_id` matches an order code or MongoDB ID.
- **Customer auto-registration from orders:** Creating an order now finds an existing customer by email (or by name + city when email is omitted), updates that customer, or creates a customer record. The order stores the matching `customer_id`, so it appears in the Customers module.
- Status options: `assigned`, `picked_up`, `out_for_delivery`, `delivered`, `cancelled`, `failed`.

To use this update, replace your project with this ZIP or copy the updated `backend/app/routes/orders.py`, `backend/app/routes/resources.py`, and `frontend/src/App.jsx` into your existing project. Restart FastAPI and Vite after replacing the files.
