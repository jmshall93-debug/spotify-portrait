# Spotify Portrait - build log

**Status:** Finished — small-project benchmark (v1.0)  
**Started:** 2026-06-06 23:05:24 +01:00  
**Finished:** 2026-06-11 17:44:44 +01:00  
**Realistic dev time:** ~2 hours

Calendar span is five days; actual hands-on building was two focused blocks. Clock only runs when you say start/stop — early micro-sessions (Jun 10) predate that rule and aren’t counted here.

| Block | When | Dev time (honest) |
|-------|------|-------------------|
| First build — scaffold through editorial UI | 2026-06-06 | ~1h |
| Final pass — palette, prose, docs, deploy | 2026-06-11 | ~1h max |
| **Total dev** | | **~2h** |

**Not dev (project overhead, same afternoon as final pass):** new GitHub account/repo, Streamlit signup, first Cloud deploy — maybe 30–45m of faff, separate from coding.

Timestamp log from the assistant summed to 2h 48m; that overcounts because the final window included multitasking and the Jun 10 segments were stop/start noise before the clock rule was clear. **~2h is the number to use for portfolio / “small project” benchmark.**

## Milestones

- Phase 1–2 — scaffold, `parse.py`, venv, smoke test
- Phase 3 — Streamlit UI, genre treemap, era + artist charts, metrics
- Visual passes — warm dark → editorial ember → ember + amber
- Phase 4 — sample CSV, upload, playlist picker, mood fingerprint
- Phase 5 — `narrate.py`, library summary, optional Groq/Ollama, deploy
- Live — Streamlit Community Cloud

## Links

- Repo: https://github.com/jmshall93-debug/spotify-portrait
- Live: https://taste-map-jbjx3umnykyhbgutasmqr6.streamlit.app/

## Later (optional)

- Upwork portfolio entry + screenshots
- AI portrait on Cloud (Groq secrets)
- Custom Streamlit URL
- Compare-two-playlists (v2)

## Data spec

### Files

| File | Purpose |
|---|---|
| `data/sample_liked_songs.csv` | Bundled demo - safe to commit |
| `data/Liked_Songs.csv` | Your private export - gitignored |
| `data/playlists/*.csv` | Local multi-playlist folder - gitignored |

Load order: upload on the main page -> playlist picker -> sample CSV.

Useful Exportify columns: `Track Name`, `Artist Name(s)`, `Release Date`, `Popularity`, `Genres`. Audio feature columns improve the mood strip.

### Optional AI portrait

Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and set one of:

- `GROQ_API_KEY` - free tier at [console.groq.com](https://console.groq.com)
- `OLLAMA_MODEL` - e.g. `llama3.2` with [Ollama](https://ollama.com) running locally

Only the stat brief goes to the model, not raw track lists. No key -> template copy.

For AI portrait on Cloud: app **Settings -> Secrets** - same keys as `secrets.toml`.

### How it works (dev)

```text
CSV -> parse.py -> taste profile + brief -> app.py (Streamlit + Plotly)
```

`parse.py` normalises Exportify columns, splits genres and artists, buckets years, and scores popularity. `narrate.py` turns the brief into copy. `app.py` renders the page.
