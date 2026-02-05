# Real-Time Shelf Stock Prediction (Zero-Shot, Pretrained)

This project detects **pen, pencil, ruler, watch** in real-time using a **pretrained zero-shot object detection model (OWL-ViT)** from Hugging Face Transformers—**no training required**. It logs detections to a SQLite database, powers a **Streamlit dashboard** for owners, generates a **PDF revenue report**, and performs **5-day sales forecasting**.

> Designed to run comfortably from Spyder (Anaconda) or the terminal.

---

## Features
- 🔍 **Pretrained zero-shot object detection (OWL-ViT)** — no dataset or training needed.
- 🎯 Only the following classes are tracked: `pen`, `pencil`, `ruler`, `watch`.
- 🧠 **Smoothing** to stabilize frame-by-frame counts.
- 🗃️ **SQLite** database to store events and daily aggregates.
- 📊 **Streamlit Dashboard** with:
  - Live-ish inventory view (polls DB)
  - Revenue accumulated (based on configurable prices)
  - 5-day demand forecast (Exponential Smoothing)
  - One-click **PDF report** generation
- 🧾 **ReportLab PDF** with KPIs and plots.
- 🧩 Modular code; easy to extend with more SKUs.

---

## Quickstart (Conda, recommended)

```bash
# 1) Create & activate env (CPU-only PyTorch for simplicity)
conda create -n shelfpred python=3.10 -y
conda activate shelfpred

# 2) Install dependencies
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
pip install transformers>=4.39.0 pillow opencv-python numpy pandas sqlalchemy streamlit statsmodels reportlab matplotlib scikit-learn

# Optional: if you have a GPU + CUDA, install the matching torch build from pytorch.org
```

> If you prefer **requirements.txt**, use:  
> `pip install -r requirements.txt`

---

## Run the detector (webcam 0 or a video file/RTSP)
```bash
# Webcam
python src/detect.py --source 0

# Or video file/stream
python src/detect.py --source path/to/video.mp4

# Optional flags
# --display          Show OpenCV window with boxes
# --commit-every N   DB commit frequency (frames)
# --skip N           Process every Nth frame (default 5)
```

## Run the dashboard
```bash
streamlit run src/dashboard.py
```
The dashboard reads from `shelf.db` and `config/prices.json`.

---

## Configuration

- **Tracked classes:** specified in `config/classes.json`.
- **Prices:** per-item prices in `config/prices.json`.
- **Smoothing:** EMA parameters in `config/config.json`.

---

## Database

SQLite DB file: `shelf.db`

Tables:
- `events(frame_ts TEXT, item TEXT, count INTEGER)` — per-processed frame counts
- `daily(item TEXT, date TEXT, units INTEGER, revenue REAL)` — daily aggregates
- `inventory(item TEXT, last_count INTEGER, updated_at TEXT)` — most recent count snapshot

---

## Forecasting

We compute daily units per item from the `events` table, then forecast the **next 5 days** using **Exponential Smoothing** (Holt-Winters, additive trend disabled by default).

---

## Generating a PDF

From the **Streamlit dashboard**, click “Generate PDF Report”, which saves into `reports/`.

You can also run:
```bash
python src/report.py --output reports/auto_report.pdf
```

---

## Push to GitHub (instructions)

```bash
# From the project root
git init
git add .
git commit -m "Initial commit: realtime shelf stock prediction (zero-shot OWL-ViT)"
git branch -M main
git remote add origin https://github.com/<your-username>/real-time-shelf-stock-prediction.git
git push -u origin main
```

---

## Notes
- OWL-ViT is strong but **small objects** (e.g., slim pens) may be challenging depending on camera quality and distance. Consider higher resolution input or ROI focusing.
- If you later want a **finetuned detector**, you can swap `owlvit` for YOLO/Detectron and keep the rest of the pipeline identical.
