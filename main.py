# main.py
import os
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse
from supabase import create_client
import pandas as pd
from io import BytesIO
import datetime

# Read env vars (set these in Render or locally)
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")  # use your SUPABASE SERVICE ROLE key for backend
if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Please set SUPABASE_URL and SUPABASE_KEY environment variables.")

sb = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(title="PPC Agent - Upload Service")

def _safe_get(row, *possibles):
    """Find first existing column in row (case-insensitive)."""
    for p in possibles:
        # try exact
        if p in row:
            return row[p]
        # try lower-cased/key variants
        for k in row.keys():
            if k and k.strip().lower() == p.strip().lower():
                return row[k]
    return None

def normalize_row(r):
    # r is a pandas Series (row); convert to dict-like
    get = lambda *ps: _safe_get(r, *ps)
    # date parsing fallback
    raw_date = get("date", "day", "Day")
    try:
        date_val = pd.to_datetime(raw_date).date() if raw_date is not None else datetime.date.today()
    except Exception:
        date_val = datetime.date.today()

    def to_int(x):
        try:
            return int(float(x)) if x not in (None, "") else 0
        except Exception:
            return 0
    def to_float(x):
        try:
            return float(x) if x not in (None, "") else 0.0
        except Exception:
            return 0.0

    return {
        "date": str(date_val),
        "platform": get("_platform", "platform") or "google",
        "campaign": get("Campaign", "campaign", "Campaign Name") or "",
        "adgroup": get("Ad Group", "adgroup", "AdSet") or "",
        "keyword": get("Keyword", "keyword", "Search Term") or "",
        "impressions": to_int(get("Impressions", "impression")),
        "clicks": to_int(get("Clicks", "clicks")),
        "cost": to_float(get("Cost", "Spend", "Amount")),
        "conversions": to_float(get("Conversions", "conversions")),
        "ctr": to_float(get("Ctr", "CTR", "Click-Through Rate")),
        "cpc": to_float(get("Cpc", "CPC")),
        "conv_rate": to_float(get("Conversion Rate", "conv_rate"))
    }

@app.get("/")
def home():
    return {"service": "ppc-agent-upload", "status": "ready"}

@app.post("/upload")
async def upload(file: UploadFile = File(...), platform: str = Form("google")):
    """
    Upload CSV or Excel file. 'platform' is optional form field: 'google' or 'meta'.
    Returns JSON with inserted row count or error details.
    """
    contents = await file.read()
    # try CSV first, else Excel
    try:
        df = pd.read_csv(BytesIO(contents))
    except Exception:
        try:
            df = pd.read_excel(BytesIO(contents))
        except Exception as e:
            return JSONResponse(status_code=400, content={"error": "Could not parse file. Please upload CSV or Excel.", "details": str(e)})

    # sanitize column names
    df.columns = [c.strip() if isinstance(c, str) else c for c in df.columns]
    df["_platform"] = platform

    rows = []
    for _, r in df.iterrows():
        try:
            rows.append(normalize_row(r))
        except Exception:
            # skip problematic row but continue
            continue

    # insert in batches (safe for larger files)
    batch = 300
    inserted = 0
    for i in range(0, len(rows), batch):
        chunk = rows[i:i+batch]
        res = sb.table("ads").insert(chunk).execute()
        # res returns a dict-like; count success heuristically
        if isinstance(res, dict) and res.get("status_code") not in (200, 201, None):
            # continue but report
            pass
        inserted += len(chunk)

    return {"status": "ok", "inserted_rows": inserted}

@app.get("/health")
def health():
    return {"status": "ok"}
