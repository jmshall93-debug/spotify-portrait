"""Spotify Portrait - Streamlit UI."""

import html
import io
import importlib
import json
import re
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

import narrate
import parse

importlib.reload(parse)
importlib.reload(narrate)
from narrate import ai_portrait, llm_configured, template_library_summary, template_portrait
from parse import analyze, analyze_file, load_csv, narrative_brief, summarize_library

DATA_DIR = Path(__file__).parent / "data"
DEFAULT_CSV = DATA_DIR / "Liked_Songs.csv"
SAMPLE_CSV = DATA_DIR / "sample_liked_songs.csv"
PLAYLISTS_DIR = DATA_DIR / "playlists"
TOP_GENRES = 10
CHART_HEIGHT = 400
SMALL_CHART_HEIGHT = 360
STRUCTURE_CHART_HEIGHT = 280

# Neutral charcoal base; ember reserved for sparse accents.
BG = "#101214"
SURFACE = "#181b1f"
SURFACE_RAISED = "#1f2328"
BORDER = "#2a3038"
BORDER_STRONG = "#3a424d"
TEXT = "#f4f2ef"
MUTED = "#9aa3ad"
BODY_TEXT = "#c8cdd4"
STAT_LABEL = "#8f98a3"
CHART_AXIS = "#8f98a3"
CHART_TITLE = "#b8c0c8"
ACCENT = "#ea580c"
ACCENT_GLOW = "#f97316"
AMBER = "#c9925a"
CREAM = "#f4f2ef"
CHART_LOW = "#162235"
CHART_HIGH = "#2f5d62"
CHART_HIGHLIGHT = "#c9925a"
STRUCTURE_STEM = "#566270"
STRUCTURE_DOT = "#47777a"
# Interleaved: ember → petrol → slate → plum — adjacent cells get different families.
GENRE_PALETTE = [
    "#7c2d12",
    "#123338",
    "#2b3645",
    "#34243a",
    "#9a3412",
    "#172a2f",
    "#1f2937",
    "#4b2a3d",
    "#a0522d",
    "#243b35",
    "#162235",
    "#5c3d4a",
    "#bf4f1f",
    "#1d3f45",
    "#3d4451",
    "#431407",
    "#2f3f3a",
]

PAGE_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
.stApp {{
    background:
        radial-gradient(ellipse 90% 55% at 18% -15%, rgba(201, 146, 90, 0.04) 0%, transparent 55%),
        {BG};
    color: {TEXT};
}}
[data-testid="stSelectbox"] label,
[data-testid="stFileUploader"] label,
[data-testid="stCheckbox"] label {{
    color: {BODY_TEXT} !important;
    font-size: 0.82rem !important;
}}
[data-testid="stSelectbox"] > div > div {{
    background: {SURFACE_RAISED} !important;
    border-color: {BORDER_STRONG} !important;
    color: {TEXT} !important;
}}
[data-testid="stFileUploaderDropzone"] {{
    background: {SURFACE_RAISED} !important;
    border-color: {BORDER_STRONG} !important;
}}
.block-container {{
    font-family: Inter, Segoe UI, system-ui, sans-serif;
    padding-top: 1.75rem;
    max-width: 1040px;
}}
#MainMenu, footer, header[data-testid="stHeader"] {{ display: none; }}
[data-testid="stSidebar"], [data-testid="collapsedControl"] {{ display: none; }}
div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] {{
    gap: 0.4rem;
}}
.control-hint {{
    color: {MUTED};
    font-size: 0.76rem;
    line-height: 1.5;
    margin: 0.15rem 0 0.65rem 0;
}}
.hero-block {{
    margin-bottom: 0.85rem;
}}
.headline-stats {{
    margin-bottom: 0.35rem;
}}
.library-context {{
    color: {MUTED};
    font-size: 0.84rem;
    line-height: 1.55;
    max-width: 52rem;
    margin: 0.5rem 0 1.25rem 0;
    padding: 0.65rem 0.85rem;
    border: 1px solid {BORDER};
    background: rgba(24, 27, 31, 0.55);
    border-radius: 8px;
}}
.library-context-label {{
    font-size: 0.58rem;
    text-transform: uppercase;
    letter-spacing: 0.14em;
    color: {STAT_LABEL};
    margin-bottom: 0.3rem;
}}
.hero-editorial {{
    border-left: 3px solid {AMBER};
    padding: 0.1rem 0 0.1rem 1rem;
    margin: 0;
}}
.hero-title {{
    font-size: 3rem;
    font-weight: 700;
    letter-spacing: -0.04em;
    line-height: 1.12;
    margin: 0 0 0.75rem 0;
    color: {TEXT};
    max-width: 22ch;
}}
.hero-label {{
    font-family: Inter, Segoe UI, system-ui, sans-serif;
    font-size: 1.05rem;
    font-weight: 500;
    line-height: 1.45;
    color: {TEXT};
    margin: 0 0 0.65rem 0;
    max-width: 38rem;
}}
.interpretation {{
    color: {MUTED};
    font-size: 0.95rem;
    line-height: 1.65;
    max-width: 38rem;
    margin: 0;
}}
.chart-note {{
    color: {MUTED};
    font-size: 0.78rem;
    margin: -0.35rem 0 0.65rem 0;
}}
.stat-strip {{
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 0.55rem;
    margin: 0 0 1rem 0;
}}
.section-label-tight {{
    margin-top: 0.5rem;
}}
@media (max-width: 720px) {{
    .block-container {{
        padding-top: 1.5rem;
        padding-left: 0.85rem;
        padding-right: 0.85rem;
    }}
    .stat-strip {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    .hero-title {{ font-size: 1.85rem; letter-spacing: -0.03em; max-width: none; }}
    .hero-label {{ font-size: 0.95rem; margin-bottom: 0.55rem; }}
    .interpretation {{ font-size: 0.9rem; line-height: 1.55; margin-bottom: 1rem; }}
    .stat-value {{ font-size: 1.15rem; }}
    .stat {{ padding: 0.65rem 0.75rem; }}
    .hero-caption {{ letter-spacing: 0.14em; font-size: 0.58rem; }}
    .control-hint {{ font-size: 0.76rem; margin-bottom: 0.75rem; }}
    .section-label {{ margin-top: 1.1rem; }}
    /* Stack side-by-side Streamlit columns */
    div[data-testid="stHorizontalBlock"] {{
        flex-wrap: wrap !important;
        gap: 0.35rem !important;
    }}
    div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {{
        flex: 1 1 100% !important;
        width: 100% !important;
        min-width: 100% !important;
    }}
    /* Compact file uploader */
    [data-testid="stFileUploaderDropzone"] {{
        padding: 0.45rem 0.6rem !important;
        min-height: 0 !important;
    }}
    [data-testid="stFileUploaderDropzone"] small {{
        display: none !important;
    }}
    [data-testid="stPlotlyChart"] {{
        padding: 0.35rem 0.5rem;
    }}
}}
@media (max-width: 420px) {{
    .hero-title {{ font-size: 1.45rem; }}
    .stat-label {{ font-size: 0.52rem; letter-spacing: 0.1em; }}
    .stat-value {{ font-size: 1rem; }}
}}
.stat {{
    background: {SURFACE};
    border: 1px solid {BORDER_STRONG};
    border-radius: 10px;
    padding: 0.8rem 1rem;
    overflow: visible;
    min-width: 0;
}}
.stat-label {{
    color: {STAT_LABEL};
    font-size: 0.58rem;
    text-transform: uppercase;
    letter-spacing: 0.14em;
    margin-bottom: 0.32rem;
    line-height: 1.3;
}}
.stat-value {{
    color: {TEXT};
    font-size: 1.35rem;
    font-weight: 600;
    letter-spacing: -0.02em;
    font-variant-numeric: tabular-nums;
    line-height: 1.2;
    padding-left: 1px;
}}
.hero-caption {{
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.22em;
    color: {AMBER};
    margin-bottom: 0.45rem;
}}
.section-label {{
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.18em;
    color: {STAT_LABEL};
    margin: 1.75rem 0 0.75rem 0;
}}
[data-testid="stPlotlyChart"] {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 0.5rem 0.75rem;
    margin-bottom: 0.35rem;
    overflow: visible;
}}
.footer-note {{
    color: {MUTED};
    font-size: 0.78rem;
    line-height: 1.5;
    margin: 2.2rem 0 0.5rem 0;
    padding-top: 1.2rem;
    border-top: 1px solid {BORDER};
}}
.stat-label-help {{
    display: flex;
    align-items: center;
    gap: 0.35rem;
}}
.metric-info {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 0.85rem;
    height: 0.85rem;
    border-radius: 50%;
    border: 1px solid {BORDER_STRONG};
    color: {MUTED};
    font-size: 0.55rem;
    font-weight: 600;
    font-style: italic;
    cursor: help;
    position: relative;
    flex-shrink: 0;
    text-transform: none;
    letter-spacing: 0;
    outline: none;
}}
.metric-info-tip {{
    visibility: hidden;
    opacity: 0;
    position: absolute;
    bottom: calc(100% + 0.4rem);
    left: 50%;
    transform: translateX(-50%);
    width: max-content;
    max-width: 14rem;
    padding: 0.45rem 0.55rem;
    background: {SURFACE_RAISED};
    border: 1px solid {BORDER_STRONG};
    border-radius: 6px;
    color: {BODY_TEXT};
    font-size: 0.72rem;
    line-height: 1.45;
    text-transform: none;
    letter-spacing: normal;
    font-weight: 400;
    font-style: normal;
    z-index: 10;
    pointer-events: none;
    transition: opacity 0.15s ease;
    box-shadow: 0 6px 18px rgba(0, 0, 0, 0.35);
}}
.metric-info:hover .metric-info-tip,
.metric-info:focus .metric-info-tip,
.metric-info:focus-visible .metric-info-tip {{
    visibility: visible;
    opacity: 1;
}}
.reset-toast {{
    color: {AMBER};
    font-size: 0.8rem;
    line-height: 1.5;
    margin: 0 0 0.75rem 0;
    padding: 0.55rem 0.75rem;
    border: 1px solid rgba(201, 146, 90, 0.35);
    border-radius: 8px;
    background: rgba(201, 146, 90, 0.08);
}}
div[data-testid="stDialog"] [data-testid="stMarkdownContainer"] p {{
    color: {BODY_TEXT};
    font-size: 0.9rem;
    line-height: 1.6;
}}
</style>
"""

CHART_LAYOUT = dict(
    margin=dict(t=48, l=12, r=12, b=12),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color=TEXT, size=12, family="Segoe UI, system-ui, sans-serif"),
    title=dict(font=dict(size=13, color=CHART_TITLE), x=0, xanchor="left"),
)


def _layout(height=CHART_HEIGHT, **extra):
    return {**CHART_LAYOUT, "height": height, **extra}


def _apply_axes(fig, show_y_grid=False):
    fig.update_xaxes(
        showgrid=False,
        linecolor=BORDER,
        tickcolor=CHART_AXIS,
        tickfont=dict(color=CHART_AXIS, size=10),
    )
    fig.update_yaxes(
        showgrid=show_y_grid,
        gridcolor=BORDER,
        gridwidth=0.5,
        zeroline=False,
        linecolor=BORDER,
        tickcolor=CHART_AXIS,
        tickfont=dict(color=CHART_AXIS, size=10),
    )
    return fig


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _lerp_hex(low: str, high: str, t: float) -> str:
    r1, g1, b1 = _hex_to_rgb(low)
    r2, g2, b2 = _hex_to_rgb(high)
    return "#{:02x}{:02x}{:02x}".format(
        int(r1 + (r2 - r1) * t),
        int(g1 + (g2 - g1) * t),
        int(b1 + (b2 - b1) * t),
    )


def _bar_fill_colors(values: list[int] | list[float], low: str, high: str) -> list[str]:
    """Solid low-to-high ramp."""
    if not values:
        return []
    vmin, vmax = min(values), max(values)
    if vmax == vmin:
        return [high] * len(values)
    return [_lerp_hex(low, high, (v - vmin) / (vmax - vmin)) for v in values]


def _bar_fill_with_highlight(
    values: list[int] | list[float],
    low: str,
    high: str,
    highlight: str,
) -> list[str]:
    """Cool ramp with one amber bar on the maximum value."""
    colors = _bar_fill_colors(values, low, high)
    if not colors:
        return colors
    peak = values.index(max(values))
    colors[peak] = highlight
    return colors


def _lollipop_colors(values: list[int] | list[float]) -> list[str]:
    """Muted dots with amber shared by tied leaders."""
    if not values:
        return []
    peak = max(values)
    return [CHART_HIGHLIGHT if value == peak else STRUCTURE_DOT for value in values]


def _lollipop_stems(
    categories: list[str],
    values: list[int] | list[float],
    horizontal: bool,
    start: float = 0,
) -> tuple[list[float | str | None], list[float | str | None]]:
    """Separated line coordinates for one lollipop stem per category."""
    first: list[float | str | None] = []
    second: list[float | str | None] = []
    for category, value in zip(categories, values):
        if horizontal:
            first.extend([start, value, None])
            second.extend([category, category, None])
        else:
            first.extend([category, category, None])
            second.extend([start, value, None])
    return first, second


def _profile_attr(profile, name: str):
    return getattr(profile, name, None)


def _pct(value: float) -> int:
    return round(value * 100)


METRIC_HELP = {
    "energy": "How intense and active the tracks feel (0–100%). Requires Spotify audio features.",
    "danceability": "How suitable the tracks are for dancing, based on rhythm and tempo (0–100%).",
    "positivity": "Musical positivity—how happy or sad the tracks sound (0–100%).",
    "tempo": "Average estimated speed in beats per minute.",
    "genres_tagged": "Number of distinct genre tags across the playlist.",
    "deep_cuts": "Distance from the mainstream: 100 minus average popularity. Higher means deeper cuts.",
}


def _stat_label_html(label: str, help_key: str | None = None) -> str:
    if not help_key:
        return f'<div class="stat-label">{label}</div>'
    tip = html.escape(METRIC_HELP[help_key])
    return (
        '<div class="stat-label stat-label-help">'
        f"<span>{label}</span>"
        f'<span class="metric-info" tabindex="0" aria-label="{tip}">i'
        f'<span class="metric-info-tip" role="tooltip">{tip}</span>'
        "</span></div>"
    )


def _mood_strip(profile) -> str:
    energy = _profile_attr(profile, "avg_energy")
    if energy is None:
        return """
    <p class="section-label section-label-tight">Mood fingerprint</p>
    <p class="chart-note">Audio features aren't included in this export, so mood stats aren't shown.</p>
    """

    tempo_val = _profile_attr(profile, "avg_tempo")
    dance_val = _profile_attr(profile, "avg_danceability")
    valence_val = _profile_attr(profile, "avg_valence")
    tempo = f"{tempo_val:.0f}" if tempo_val is not None else "—"
    dance = _pct(dance_val) if dance_val is not None else "—"
    valence = _pct(valence_val) if valence_val is not None else "—"
    return f"""
    <p class="section-label section-label-tight">Mood fingerprint</p>
    <div class="stat-strip">
        <div class="stat">
            {_stat_label_html("Energy", "energy")}
            <div class="stat-value">{_pct(energy)}%</div>
        </div>
        <div class="stat">
            {_stat_label_html("Danceability", "danceability")}
            <div class="stat-value">{dance}%</div>
        </div>
        <div class="stat">
            {_stat_label_html("Positivity", "positivity")}
            <div class="stat-value">{valence}%</div>
        </div>
        <div class="stat">
            {_stat_label_html("Tempo", "tempo")}
            <div class="stat-value">{tempo}<span style="font-size:0.75rem;color:{MUTED};"> bpm</span></div>
        </div>
    </div>
    """


def _stat_card(
    label: str,
    value: str,
    accent: bool = False,
    help_key: str | None = None,
) -> str:
    value_style = f' style="color: {ACCENT_GLOW};"' if accent else ""
    return (
        '<div class="stat">'
        f"{_stat_label_html(label, help_key)}"
        f'<div class="stat-value"{value_style}>{value}</div>'
        "</div>"
    )


def _primary_stat_strip(profile) -> str:
    genre_count = profile.stats.unique_genres
    genre_value = str(genre_count) if genre_count else "—"
    cards = (
        _stat_card("Tracks", str(profile.track_count))
        + _stat_card("Genre tags", genre_value, help_key="genres_tagged")
        + _stat_card("Unique artists", str(profile.artist_count))
        + _stat_card("Deep cuts index", str(profile.obscurity_score), accent=True, help_key="deep_cuts")
    )
    return f'<div class="stat-strip headline-stats">{cards}</div>'


def _hero_editorial_block(portrait, source_label: str, ai_note: str) -> str:
    label_html = ""
    if portrait.label.strip():
        label_html = f'<p class="hero-label">{portrait.label}</p>'
    return (
        '<div class="hero-editorial">'
        f'<p class="hero-caption">Spotify Portrait / {source_label}{ai_note}</p>'
        f'<h1 class="hero-title">{portrait.title}</h1>'
        f"{label_html}"
        f'<p class="interpretation">{portrait.interpretation}</p>'
        "</div>"
    )


def _playlist_label(path: Path) -> str:
    name = path.stem.replace("_", " ")
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", name)


def _playlist_choices() -> list[tuple[str, Path]]:
    private_paths = _private_export_paths()
    if private_paths:
        return [
            (_playlist_label(path), path)
            for path in sorted(private_paths, key=lambda p: _playlist_label(p).lower())
        ]
    if SAMPLE_CSV.exists():
        return [("Sample playlist", SAMPLE_CSV)]
    return []


def _default_playlist_index(choices: list[tuple[str, Path]]) -> int:
    labels = [label.lower() for label, _ in choices]
    for preferred in ("liked songs", "sample playlist"):
        if preferred in labels:
            return labels.index(preferred)
    return 0


def _library_playlist_paths() -> list[Path]:
    return sorted(_private_export_paths(), key=lambda p: _playlist_label(p).lower())


def _private_export_paths() -> list[Path]:
    paths: list[Path] = []
    if DEFAULT_CSV.exists():
        paths.append(DEFAULT_CSV)
    if PLAYLISTS_DIR.is_dir():
        paths.extend(sorted(PLAYLISTS_DIR.glob("*.csv")))
    return paths


def _safe_playlist_stem(filename: str) -> str:
    stem = Path(filename).stem
    stem = re.sub(r"[^A-Za-z0-9]+", "_", stem).strip("_")
    return stem[:80] or "Playlist"


def _save_playlist_contents(filename: str, contents: bytes) -> Path:
    """Save one validated upload without overwriting a different playlist."""
    PLAYLISTS_DIR.mkdir(parents=True, exist_ok=True)

    stem = _safe_playlist_stem(filename)
    candidate = PLAYLISTS_DIR / f"{stem}.csv"
    suffix = 2
    while candidate.exists() and candidate.read_bytes() != contents:
        candidate = PLAYLISTS_DIR / f"{stem}_{suffix}.csv"
        suffix += 1
    if not candidate.exists():
        candidate.write_bytes(contents)
    return candidate


def _save_uploaded_playlists(uploaded_files) -> list[Path]:
    """Validate a batch before saving its playlists to the private library."""
    uploads = [(uploaded.name, uploaded.getvalue()) for uploaded in uploaded_files]
    for _filename, contents in uploads:
        analyze(load_csv(io.BytesIO(contents)))
    return [_save_playlist_contents(filename, contents) for filename, contents in uploads]


def _user_data_present(nonce: int) -> bool:
    if st.session_state.get(f"csv_upload_{nonce}"):
        return True
    return bool(_private_export_paths())


def _reset_success_message(removed: int, had_upload: bool) -> str:
    parts: list[str] = []
    if removed:
        parts.append("Your saved playlists have been removed.")
    if had_upload:
        parts.append("Your uploaded file has been cleared.")
    if not parts:
        return "You're back on the sample playlist."
    return " ".join(parts) + " You're now viewing the sample playlist."


def _execute_library_reset(had_upload: bool) -> tuple[bool, str]:
    errors: list[str] = []
    removed = 0
    for path in _private_export_paths():
        try:
            path.unlink()
            removed += 1
        except OSError as exc:
            errors.append(f"{_playlist_label(path)} ({exc})")

    _cached_library_summary.clear()
    _cached_ai_portrait.clear()
    st.session_state.reset_nonce = st.session_state.get("reset_nonce", 0) + 1
    st.session_state.pop("reset_confirm_pending", None)

    if errors:
        return (
            False,
            "Some playlists couldn't be removed. Close any open files and try again.",
        )
    return True, _reset_success_message(removed, had_upload)


@st.dialog("Clear your playlists?")
def _clear_playlists_dialog(had_upload: bool) -> None:
    st.markdown(
        "This removes any playlists saved on this device and clears anything you've uploaded. "
        "The sample playlist stays available so you can keep exploring."
    )
    keep_col, clear_col = st.columns(2)
    with keep_col:
        if st.button("Keep my playlists", use_container_width=True, key="reset_dialog_keep"):
            st.rerun()
    with clear_col:
        if st.button("Clear everything", type="primary", use_container_width=True, key="reset_dialog_clear"):
            ok, message = _execute_library_reset(had_upload)
            st.session_state.reset_status = ("success" if ok else "error", message)
            st.rerun()


@st.cache_data(show_spinner=False)
def _cached_library_summary(path_key: tuple[str, ...]) -> str:
    paths = [Path(p) for p in path_key]
    entries = [(_playlist_label(path), analyze_file(path)) for path in paths]
    summary = summarize_library(entries)
    return template_library_summary(summary)


def _llm_settings() -> tuple[str | None, str | None]:
    groq_key = None
    ollama_model = None
    try:
        groq_key = st.secrets.get("GROQ_API_KEY")
        ollama_model = st.secrets.get("OLLAMA_MODEL")
    except (FileNotFoundError, AttributeError, KeyError):
        pass
    return groq_key, ollama_model


@st.cache_data(show_spinner="Writing AI portrait…")
def _cached_ai_portrait(brief_json: str, groq_key: str | None, ollama_model: str | None):
    brief = json.loads(brief_json)
    return ai_portrait(brief, groq_api_key=groq_key, ollama_model=ollama_model)


def _resolve_portrait(profile, source_label: str, use_ai: bool):
    brief = narrative_brief(profile, source_label)
    portrait = template_portrait(profile, brief)
    if not use_ai:
        return portrait, brief

    groq_key, ollama_model = _llm_settings()
    ai = _cached_ai_portrait(json.dumps(brief, sort_keys=True), groq_key, ollama_model)
    if ai:
        return ai, brief
    st.warning("AI portrait unavailable. Showing the standard summary.")
    return portrait, brief


def _load_profile():
    if "reset_nonce" not in st.session_state:
        st.session_state.reset_nonce = 0

    reset_status = st.session_state.pop("reset_status", None)
    if reset_status:
        level, message = reset_status
        if level == "success":
            st.markdown(f'<p class="reset-toast">{html.escape(message)}</p>', unsafe_allow_html=True)
        else:
            st.error(message)

    choices = _playlist_choices()
    if not choices:
        st.error("Upload an Exportify CSV to get started.")
        st.stop()

    labels = [label for label, _ in choices]
    groq_key, ollama_model = _llm_settings()
    ai_available = llm_configured(groq_key, ollama_model)
    nonce = st.session_state.reset_nonce
    pending_playlist = st.session_state.pop("pending_playlist", None)
    selected_index = (
        labels.index(pending_playlist)
        if pending_playlist in labels
        else _default_playlist_index(choices)
    )

    if ai_available:
        pick_col, upload_col, ai_col = st.columns([4, 4, 2])
    else:
        pick_col, upload_col = st.columns([5, 4])
        ai_col = None
    with pick_col:
        picked = st.selectbox(
            "Playlist",
            labels,
            index=selected_index,
            key=f"playlist_pick_{nonce}",
        )
    with upload_col:
        uploaded_files = st.file_uploader(
            "Upload playlists",
            type=["csv"],
            accept_multiple_files=True,
            help="Save one or more Exportify CSVs to your local library.",
            key=f"csv_upload_{nonce}",
        )
    use_ai = False
    if ai_available:
        with ai_col:
            use_ai = st.checkbox("AI portrait", value=False, key=f"ai_portrait_{nonce}")

    if uploaded_files:
        try:
            paths = _save_uploaded_playlists(uploaded_files)
            st.session_state.pending_playlist = _playlist_label(paths[0])
            _cached_library_summary.clear()
            count = len(paths)
            st.session_state.reset_status = (
                "success",
                f"Added {count} playlist{'s' if count != 1 else ''}.",
            )
            st.session_state.reset_nonce = nonce + 1
            st.rerun()
        except Exception as exc:
            st.error(f"Couldn't read one or more CSV files: {exc}")
            st.stop()

    path = dict(choices)[picked]
    return analyze_file(path), picked, use_ai


def genre_treemap(profile):
    weights = profile.genre_weights
    if weights.empty:
        return None

    top = weights.head(TOP_GENRES)
    genres = top.index.tolist()
    counts = [int(v) for v in top.values.tolist()]
    colors = [GENRE_PALETTE[i % len(GENRE_PALETTE)] for i in range(len(genres))]

    fig = go.Figure(
        go.Treemap(
            labels=genres,
            parents=[""] * len(genres),
            values=counts,
            branchvalues="total",
            marker=dict(colors=colors, line=dict(color=BG, width=1)),
            textfont=dict(color=CREAM, size=12, family="Inter, Segoe UI, system-ui, sans-serif"),
            texttemplate="%{label}<br>%{percentRoot:.0%}",
            textinfo="text",
            insidetextfont=dict(color=CREAM, size=12),
            tiling=dict(pad=11),
        )
    )
    fig.update_layout(
        height=CHART_HEIGHT,
        margin=dict(t=12, l=14, r=14, b=8),
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        font=dict(color=TEXT, size=12, family="Inter, Segoe UI, system-ui, sans-serif"),
        uniformtext=dict(minsize=10, mode="hide"),
    )
    return fig


def era_bar(profile):
    buckets = profile.era_buckets
    if buckets.empty:
        return None

    eras = buckets.index.tolist()
    values = buckets.values.tolist()
    stem_x, stem_y = _lollipop_stems(eras, values, horizontal=False)
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=stem_x,
            y=stem_y,
            mode="lines",
            line=dict(color=STRUCTURE_STEM, width=2),
            hoverinfo="skip",
            showlegend=False,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=eras,
            y=values,
            mode="markers+text",
            marker=dict(
                color=_lollipop_colors(values),
                size=15,
                line=dict(color=SURFACE, width=2),
            ),
            text=[str(value) for value in values],
            textposition="top center",
            textfont=dict(color=BODY_TEXT, size=11),
            hovertemplate="%{x}: %{y} tracks<extra></extra>",
            showlegend=False,
        )
    )
    top = max(values)
    fig.update_layout(
        **_layout(
            height=STRUCTURE_CHART_HEIGHT,
            margin=dict(t=52, l=20, r=20, b=44),
            paper_bgcolor=SURFACE,
            plot_bgcolor=SURFACE,
            xaxis_title=None,
            yaxis_title=None,
        )
    )
    fig.update_layout(title=dict(text="Release decades", font=dict(size=13, color=CHART_TITLE), x=0, xanchor="left"))
    fig.update_xaxes(categoryorder="array", categoryarray=eras)
    fig.update_yaxes(visible=False, range=[0, top + max(2, top * 0.18)], fixedrange=True)
    return fig


def top_artists_bar(profile, limit: int = 8):
    artists = profile.top_artists.head(limit).sort_values(ascending=True)
    if artists.empty:
        return None

    names = artists.index.tolist()
    values = artists.values.tolist()
    top = max(values)
    stem_start = max(0.12, top * 0.025)
    stem_x, stem_y = _lollipop_stems(names, values, horizontal=True, start=stem_start)
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=stem_x,
            y=stem_y,
            mode="lines",
            line=dict(color=STRUCTURE_STEM, width=2),
            hoverinfo="skip",
            showlegend=False,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=values,
            y=names,
            mode="markers+text",
            marker=dict(
                color=_lollipop_colors(values),
                size=15,
                line=dict(color=SURFACE, width=2),
            ),
            text=[str(value) for value in values],
            textposition="middle right",
            textfont=dict(color=BODY_TEXT, size=11),
            hovertemplate="%{y}: %{x} tracks<extra></extra>",
            showlegend=False,
        )
    )
    fig.update_layout(
        **_layout(
            height=SMALL_CHART_HEIGHT,
            margin=dict(t=42, l=156, r=42, b=18),
            paper_bgcolor=SURFACE,
            plot_bgcolor=SURFACE,
        )
    )
    fig.update_layout(title=dict(text=f"Top {limit} artists", font=dict(size=13, color=CHART_TITLE), x=0, xanchor="left"))
    fig.update_xaxes(visible=False, range=[0, top + max(1, top * 0.18)], fixedrange=True)
    fig.update_yaxes(
        automargin=True,
        categoryorder="array",
        categoryarray=names,
        fixedrange=True,
        showgrid=False,
        tickfont=dict(color=CHART_AXIS, size=10),
    )
    return fig


st.set_page_config(
    page_title="Spotify Portrait",
    layout="wide",
    page_icon="♪",
    initial_sidebar_state="collapsed",
)

st.markdown(PAGE_CSS, unsafe_allow_html=True)

profile, source_label, use_ai = _load_profile()
portrait, _brief = _resolve_portrait(profile, source_label, use_ai)

library_paths = _library_playlist_paths()
library_summary = ""
if len(library_paths) >= 2:
    path_key = tuple(str(p.resolve()) for p in library_paths)
    library_summary = _cached_library_summary(path_key)

ai_note = f" · {portrait.source} portrait" if portrait.source != "template" else ""

nonce = st.session_state.reset_nonce
had_upload = bool(st.session_state.get(f"csv_upload_{nonce}"))
show_clear = _user_data_present(nonce)

hint_col, clear_col = st.columns([5.5, 1.5])
with hint_col:
    st.markdown(
        '<p class="control-hint">Choose a playlist or upload '
        '<a href="https://exportify.net" style="color:#c9925a;">Exportify</a> CSVs.</p>',
        unsafe_allow_html=True,
    )
with clear_col:
    if show_clear:
        if st.button(
            "Clear my playlists",
            type="secondary",
            help="Remove saved playlists and any uploaded file. The sample playlist stays.",
            key=f"clear_open_{nonce}",
        ):
            _clear_playlists_dialog(had_upload)

st.markdown(
    f'<div class="hero-block">{_hero_editorial_block(portrait, source_label, ai_note)}</div>',
    unsafe_allow_html=True,
)
st.markdown(_primary_stat_strip(profile), unsafe_allow_html=True)

st.markdown(_mood_strip(profile), unsafe_allow_html=True)

if library_summary:
    st.markdown(
        f'<p class="library-context-label">Library context</p>'
        f'<p class="library-context">{library_summary}</p>',
        unsafe_allow_html=True,
    )

genre_total = len(profile.genre_weights)
st.markdown('<p class="section-label">Top genres</p>', unsafe_allow_html=True)
st.markdown(
    f'<p class="chart-note">Top {min(TOP_GENRES, genre_total)} of {genre_total} tagged genres</p>',
    unsafe_allow_html=True,
)
genre_fig = genre_treemap(profile)
if genre_fig is None:
    st.warning("This playlist has no genre tags.")
else:
    st.plotly_chart(
        genre_fig,
        width="stretch",
        height=CHART_HEIGHT,
        theme=None,
        config={"displayModeBar": False, "responsive": True},
    )

st.markdown('<p class="section-label">Structure</p>', unsafe_allow_html=True)
artists_fig = top_artists_bar(profile)
if artists_fig is None:
    st.warning("This playlist has no artist data.")
else:
    st.plotly_chart(artists_fig, width="stretch", theme=None, config={"displayModeBar": False})

era_fig = era_bar(profile)
if era_fig is None:
    st.warning("This playlist has no release dates.")
else:
    st.plotly_chart(era_fig, width="stretch", theme=None, config={"displayModeBar": False})

st.markdown(
    '<p class="footer-note">Deep cuts index = 100 minus average Spotify popularity '
    '(higher means deeper cuts). '
    '<a href="https://github.com/jmshall93-debug/spotify-portrait" style="color: #f97316;">Source on GitHub</a>.</p>',
    unsafe_allow_html=True,
)
