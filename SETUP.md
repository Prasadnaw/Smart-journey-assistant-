# Setup Guide (Windows / PowerShell)

Tested for Python 3.10–3.13. If you're on Python 3.14 and a package below
fails to build, see the note at the bottom.

## 1. Backend

```powershell
cd journeyai-india\backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
python -m uvicorn main:app --reload
```

Backend now runs at **http://localhost:8000**. Check it:

```powershell
curl http://localhost:8000/health
curl http://localhost:8000/api/status
```

No API keys are required for the app to work — every default provider
(Open-Meteo, Photon, OSRM, Overpass, Transitous, Wikipedia) is free and
keyless. `.env.example` lists the optional keys (Transitland, a local GTFS
feed) that unlock official data for a specific transit agency.

## 2. Frontend

Open a **second** PowerShell window:

```powershell
cd journeyai-india\frontend
npm install
npm run dev
```

Frontend runs at **http://localhost:5173** and proxies `/api/*` and
`/health` to the backend automatically (see `vite.config.js`).

## 3. Try it

1. Open http://localhost:5173
2. Type a location in **FROM** (or click "Use current location")
3. Type a destination in **TO**
4. Pick a priority (fastest / cheapest / fewest changes / least walking / greenest)
5. Click **Find smartest route →**

## 4. Running backend tests

```powershell
cd journeyai-india\backend
.\venv\Scripts\Activate.ps1
pytest
```

## 5. Production build check

```powershell
cd journeyai-india\frontend
npm run build
```

This must complete without errors before a deploy — it's also the exact
command used to verify this project during development.

## Python 3.14 note

`requirements.txt` uses minimum versions (`pydantic>=2.12.0` etc.) rather
than old exact pins, because Python 3.14 support (prebuilt wheels for
`pydantic-core`, no Rust compiler needed) only landed in pydantic 2.12+.
`pip install -r requirements.txt` will pull the latest compatible
versions automatically.

If your `venv` was created **before** you fixed this and `pip install`
partially failed, delete it and start clean so nothing half-installed is
left behind:

```powershell
deactivate
Remove-Item -Recurse -Force venv
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

If a package still tries to build from source on 3.14 (rare, but possible
for a dependency that hasn't shipped 3.14 wheels yet), the simplest fix is
to install Python 3.12 or 3.13 from python.org and create the venv with
that interpreter instead: `py -3.12 -m venv venv`.

**Note on pasting commands:** copy only the actual command lines below —
don't paste triple-backtick fences (```` ``` ````) from a chat/markdown
window into PowerShell; they aren't valid commands and will error with
"The term '`' is not recognized".
