# StoreDash MVP v0.2 — Call Center Workspace

This version is the **call-center operator workspace**.

## What changed

- Removed the Employees page from the call-center navigation.
- Employee creation/assignment remains an admin concern for a later admin workspace.
- New customers receive an automatic StoreDash customer number starting at `000`, then `001`, `002`, ...
- Customer search supports customer number, owner name, business name, and phone.
- Customer profiles show full saved details and complete StoreDash order history.
- New Order now searches/selects a customer instead of asking operators for an internal database ID.
- Suppliers receive an automatic StoreDash supplier number starting at `000`.
- Supplier search supports supplier number, name, phone, contact person, and category.
- Supplier profiles show saved supplier details and transaction history once order items are assigned to that supplier.
- Orders have readable IDs like `SD-000001`.

The customer/supplier numbers are derived from internal IDs and are zero-padded for operators. Do not delete records during the pilot if you want those numbers to remain a simple permanent sequence.

## Run the backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Windows activation:

```bash
.venv\Scripts\activate
```

API: `http://localhost:8000`
Swagger: `http://localhost:8000/docs`

## Run the frontend

Open another terminal:

```bash
cd frontend
npm install
```

Create `.env.local` with:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api
```

Then:

```bash
npm run dev
```

Frontend: `http://localhost:3000`

## Important MVP note

This version visually separates the call-center workspace from employee administration, but **login/role enforcement is not wired yet**. The next auth/admin slice should ensure only users assigned the call-center role can enter this workspace.
