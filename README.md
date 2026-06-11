# Taste Map

Taste Map turns a Spotify / Exportify-style CSV into an editorial portrait of a music collection: genre weight, release-era shape, artist concentration, and a "deep cuts" index based on Spotify popularity.

It is built as a small portfolio demo: fast to run, easy to inspect, and designed for clean handover.

## What It Does

- Reads a Spotify liked-songs or playlist CSV export.
- Builds a one-page visual report with genre, era, artist, and popularity signals.
- Includes a bundled sample CSV so the app works without private data.
- Lets a user upload their own CSV from the sidebar.

## Data Flow

```text
CSV export -> parse.py -> derived taste profile -> app.py -> Streamlit report
```

`parse.py` is the engine: it normalizes columns, splits genres/artists, buckets release years by decade, and calculates the deep-cuts score.

`app.py` is the presentation layer: it renders the report with Streamlit and Plotly.

## Run Locally

```powershell
cd "C:\AI dreams\business\taste-map"
.\.venv\Scripts\python.exe -m streamlit run app.py
```

If setting up from scratch:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

## Data Files

- `data/sample_liked_songs.csv` is safe demo data for a public repo.
- `data/Liked_Songs.csv` is a private local export and is ignored by git.

The app uses this priority:

1. Uploaded CSV from the sidebar.
2. Local private `data/Liked_Songs.csv`, if present.
3. Bundled sample `data/sample_liked_songs.csv`.

## Expected CSV Columns

The parser expects Exportify-style columns such as:

- `Track Name`
- `Artist Name(s)`
- `Release Date`
- `Popularity`
- `Genres`

It tolerates a few common naming variants, but the richer the export, the better the portrait.

## Deploy

Git is installed on this laptop. From the project folder:

```powershell
cd "C:\AI dreams\business\taste-map"
git init
git add app.py parse.py requirements.txt README.md .gitignore .streamlit/config.toml data/sample_liked_songs.csv BUILD_LOG.md
git commit -m "Initial Taste Map portfolio demo"
```

Create a new public GitHub repo (e.g. `taste-map`), then:

```powershell
git remote add origin https://github.com/YOUR_USERNAME/taste-map.git
git branch -M main
git push -u origin main
```

Do **not** commit `.venv/`, `__pycache__/`, or `data/Liked_Songs.csv` — they are in `.gitignore`.

On first use, Git may ask for your name and email (`git config --global user.name` / `user.email`).

Then in Streamlit Community Cloud, create a new app from that repo and set:

- Main file path: `app.py`

The deployed app will use the bundled sample data by default, and visitors can upload their own Exportify CSV from the sidebar.

## Handover Notes

A client version would include:

- Full source code.
- Sample/demo data.
- Setup instructions.
- Clear notes on private files vs public demo files.
- Optional customization: branding, copy tone, extra charts, or multi-playlist comparison.

The goal is no lock-in: the owner can run, inspect, and modify the app without depending on the original builder.

## Portfolio Copy

**Listening Taste Map — visual portrait from a Spotify export**

Independent demonstration build. Upload a Spotify/Exportify CSV and get a one-page taste portrait: genre composition, release-era shape, top artists, and a deep-cuts index. Built with a clean separation between parsing logic and presentation, plus sample data and run instructions for handover.
