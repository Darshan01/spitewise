# Spitewise Web App

Group expense splitting web app with Google sign-in and receipt scanning.

---

## Project structure

```
spitewise/
├── app.py                  # Flask app factory + entry point
├── db.py                   # MongoDB connection helpers
├── debt_calculator.py      # Core calculation logic (ported from spitewise.py)
├── models.py               # User model (Flask-Login)
├── routes/
│   ├── auth.py             # GET /login, GET /auth/google, GET /auth/callback, POST /logout
│   ├── groups.py           # GET|POST /groups, GET|DELETE /groups/<id>, POST /groups/<id>/members
│   ├── transactions.py     # GET|POST /groups/<id>/transactions, PUT|DELETE /transactions/<id>
│   ├── summary.py          # GET /groups/<id>/summary
│   └── receipts.py         # POST /scan-receipt
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── groups.html
│   └── group_detail.html
├── static/
│   ├── css/main.css
│   └── js/main.js
├── requirements.txt
├── render.yaml             # Render.com deployment config
├── .env.example            # Copy to .env and fill in secrets
└── .gitignore
```

---

## Local development

### 1. Clone and install

```bash
git clone <your-repo-url> spitewise
cd spitewise
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Set up environment variables

```bash
cp .env.example .env
# Open .env and fill in all values (see below for how to get each one)
```

### 3. MongoDB Atlas (free)

1. Go to [mongodb.com/atlas](https://www.mongodb.com/atlas) → create a free account
2. Create a free M0 cluster (any region)
3. Under **Database Access**, create a user with read/write privileges
4. Under **Network Access**, add `0.0.0.0/0` (allow all IPs) for development
5. Click **Connect** → **Drivers** → copy the connection string
6. Paste it into `MONGODB_URI` in `.env`, replacing `<password>` with your DB user's password

### 4. Google OAuth credentials

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a project (or use an existing one)
3. Enable the **Google+ API** (or **People API**)
4. Go to **APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID**
5. Application type: **Web application**
6. Authorized redirect URIs: add `http://localhost:5000/auth/callback`
7. Copy **Client ID** and **Client Secret** into `.env`

### 5. Google Cloud Vision API (for receipt scanning)

1. In the same Google Cloud project, enable the **Cloud Vision API**
2. Go to **APIs & Services → Credentials → Create Credentials → API Key**
3. (Optional but recommended) Restrict the key to the Cloud Vision API
4. Copy the key into `VISION_API_KEY` in `.env`

### 6. Run

```bash
python app.py
```

Open [http://localhost:5000](http://localhost:5000).

---

## Deploying to Render.com (free tier)

1. Push your code to a GitHub repository (make sure `.env` is in `.gitignore` — it is)
2. Go to [render.com](https://render.com) → **New → Web Service**
3. Connect your GitHub repo
4. Render detects `render.yaml` automatically
5. In the **Environment** tab, fill in the four secret variables:
   - `MONGODB_URI`
   - `GOOGLE_CLIENT_ID`
   - `GOOGLE_CLIENT_SECRET`
   - `VISION_API_KEY`
6. Click **Deploy**

Your app will be live at `https://spitewise.onrender.com` (or similar).

**Before going live:** go back to your Google OAuth credentials and add your Render URL to the Authorized Redirect URIs:
```
https://your-app-name.onrender.com/auth/callback
```

---

## API reference

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/login` | Login page |
| GET | `/auth/google` | Start Google OAuth |
| GET | `/auth/callback` | OAuth callback |
| POST | `/logout` | Sign out |
| GET | `/groups` | Dashboard — list user's groups |
| POST | `/groups` | Create group `{name}` |
| GET | `/groups/<id>` | Group detail page |
| POST | `/groups/<id>/members` | Add member `{email}` |
| DELETE | `/groups/<id>` | Delete group (creator only) |
| GET | `/groups/<id>/transactions` | List transactions (JSON) |
| POST | `/groups/<id>/transactions` | Add transaction `{paid_by, amount, description, split_among[]}` |
| PUT | `/transactions/<id>` | Edit transaction |
| DELETE | `/transactions/<id>` | Delete transaction |
| GET | `/groups/<id>/summary?simplify=true` | Run debt calculator, return JSON |
| POST | `/scan-receipt` | Upload receipt image, returns parsed `{description, amount, line_items}` |

---

## Python version

3.11+ recommended (tested on 3.13). Render uses 3.11 by default.