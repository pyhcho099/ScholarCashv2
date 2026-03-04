# 🚀 Deployment Guide — ScholarCash v2

---

## 📋 Table of Contents

1. [Local Development](#1-local-development)
2. [Vercel — Preview / Demo](#2-vercel--preview--demo)
3. [Production — Full Deployment](#3-production--full-deployment)

---

## 1. Local Development

### Requirements
- Python 3.10+
- pip

### Steps

```bash
# Clone and enter the project
git clone https://github.com/pyhcho099/ScholarCashv2.git
cd ScholarCashv2

# Create virtual environment
python -m venv venv
source venv/bin/activate        # macOS/Linux
venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py
```

App runs at **http://localhost:5000**

Default login: `principal@school.com` / `admin`

> SQLite database is auto-created at `instance/scholarcash_v2.db` on first run.

---

## 2. Vercel — Preview / Demo

> ⚠️ **Preview mode only** — SQLite does not work on Vercel's serverless infrastructure. The app will show a friendly "Database not connected" page for routes that require DB access. The landing page is still visible.

### Requirements
- A GitHub account
- A Vercel account (free tier is fine)

### Steps

**Step 1 — Make sure `vercel.json` exists in your project root:**

```json
{
  "version": 2,
  "builds": [
    {
      "src": "app.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "app.py"
    }
  ]
}
```

**Step 2 — Make sure `templates/db_offline.html` exists:**

```html
<!DOCTYPE html>
<html>
<head><title>ScholarCash - Preview Mode</title></head>
<body style="font-family:sans-serif; text-align:center; padding:50px">
  <h2>⚠️ Preview Mode</h2>
  <p>Database is not connected in this preview environment.</p>
  <p>This is a UI demo only.</p>
  <a href="/landing">← Back to Landing Page</a>
</body>
</html>
```

**Step 3 — Push to GitHub:**

```bash
git add .
git commit -m "Add Vercel deployment config"
git push origin main
```

**Step 4 — Deploy on Vercel:**

1. Go to [vercel.com](https://vercel.com) and sign in with GitHub
2. Click **Add New Project**
3. Import your `ScholarCashv2` repository
4. Click **Deploy**

You'll get a live URL like `scholar-cashv2.vercel.app` in about a minute.

### What works on Vercel

| Feature | Status |
|---|---|
| Landing page (`/landing`) | ✅ Works |
| Login / Register | ❌ Needs DB |
| Dashboards | ❌ Needs DB |
| Store | ❌ Needs DB |

---

## 3. Production — Full Deployment

For a fully working deployment with persistent data, you need a hosted PostgreSQL database.

### Recommended Stack
- **Platform:** [Render](https://render.com) or [Railway](https://railway.app) (both have free tiers)
- **Database:** [Supabase](https://supabase.com) PostgreSQL (free tier)

---

### Step 1 — Set up Supabase (PostgreSQL)

1. Go to [supabase.com](https://supabase.com) and create a free account
2. Create a new project
3. Go to **Settings → Database**
4. Copy the **Connection String (URI)** — it looks like:
   ```
   postgresql://postgres:[PASSWORD]@db.[PROJECT].supabase.co:5432/postgres
   ```

---

### Step 2 — Update `app.py`

Replace the SQLite URI with an environment variable:

```python
import os

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL',
    'sqlite:///scholarcash_v2.db'  # fallback for local dev
)
```

> This way local development still uses SQLite automatically.

---

### Step 3 — Install PostgreSQL driver

```bash
pip install psycopg2-binary
pip freeze > requirements.txt
```

---

### Step 4 — Deploy on Render

1. Go to [render.com](https://render.com) and sign in with GitHub
2. Click **New → Web Service**
3. Connect your `ScholarCashv2` repo
4. Set these options:
   - **Runtime:** Python
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
5. Under **Environment Variables**, add:
   ```
   DATABASE_URL = postgresql://postgres:[PASSWORD]@db.[PROJECT].supabase.co:5432/postgres
   SECRET_KEY   = your-strong-secret-key-here
   ```
6. Click **Deploy**

---

### Step 5 — Install Gunicorn

```bash
pip install gunicorn
pip freeze > requirements.txt
git add requirements.txt
git commit -m "Add gunicorn for production"
git push origin main
```

---

### Security Checklist Before Going Live

- [ ] Change `SECRET_KEY` to a long random string
- [ ] Change default principal password (`admin` → something strong)
- [ ] Set `debug=False` in `app.run()`
- [ ] Use environment variables for all secrets (never hardcode)
- [ ] Add HTTPS (Render/Vercel handle this automatically)

---

## 🔁 Updating the App

After any code change:

```bash
git add .
git commit -m "describe your change"
git push origin main
```

Vercel and Render auto-deploy on every push to `main`. ✅
