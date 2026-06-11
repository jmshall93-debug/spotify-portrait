"""Taste Map — Streamlit UI."""

from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

from parse import analyze, analyze_file, load_csv

DEFAULT_CSV = Path(__file__).parent / "data" / "Liked_Songs.csv"
SAMPLE_CSV = Path(__file__).parent / "data" / "sample_liked_songs.csv"
TOP_GENRES = 18
CHART_HEIGHT = 430
SMALL_CHART_HEIGHT = 330

# Editorial Ember: orange is the heat, petrol/slate is the counterweight.
BG = "#050504"
SURFACE = "#100f0d"
BORDER = "#2d241d"
TEXT = "#fff8f0"
MUTED = "#a08b78"
ACCENT = "#ea580c"
ACCENT_DEEP = "#7c2d12"
ACCENT_GLOW = "#f97316"
PETROL = "#123338"
PETROL_LIGHT = "#2f5d62"
PLUM = "#34243a"
CREAM = "#fff8f0"
BAR_LOW = "#431407"
BAR_HIGH = "#ea580c"
# Deep mixed palette: ember, tobacco, petrol, slate, plum.
GENRE_PALETTE = [
    "#431407",
    "#123338",
    "#7c2d12",
    "#1f2937",
    "#9a3412",
    "#243b35",
    "#34243a",
    "#a0522d",
    "#172a2f",
    "#702500",
    "#2b3645",
    "#571f0a",
    "#2f3f3a",
    "#4b2a3d",
    "#bf4f1f",
    "#162235",
    "#d4622a",
    "#1d3f45",
]

PAGE_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
.stApp {{
    background:
        radial-gradient(ellipse 90% 55% at 18% -15%, rgba(234, 88, 12, 0.20) 0%, transparent 55%),
        radial-gradient(ellipse 80% 50% at 92% 8%, rgba(18, 51, 56, 0.34) 0%, transparent 58%),
        {BG};
    color: {TEXT};
}}
.block-container {{
    font-family: Inter, Segoe UI, system-ui, sans-serif;
    padding-top: 2.1rem;
    max-width: 1040px;
}}
#MainMenu, footer, header {{ visibility: hidden; }}

.hero-title {{
    font-size: 2.55rem;
    font-weight: 600;
    letter-spacing: -0.045em;
    margin: 0 0 0.35rem 0;
    color: {TEXT};
}}
.hero-label {{
    font-family: Inter, Segoe UI, system-ui, sans-serif;
    font-size: 1.05rem;
    font-weight: 500;
    line-height: 1.45;
    color: {ACCENT_GLOW};
    margin: 0 0 0.8rem 0;
    max-width: 50rem;
}}
.interpretation {{
    color: {MUTED};
    font-size: 0.98rem;
    line-height: 1.65;
    max-width: 52rem;
    margin: 0 0 1.55rem 0;
}}
.stat-strip {{
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 1px;
    background: {BORDER};
    border: 1px solid {BORDER};
    border-radius: 8px;
    overflow: hidden;
    margin: 1.55rem 0 1.35rem 0;
}}
.stat {{
    background: rgba(18, 16, 13, 0.92);
    padding: 0.8rem 0.95rem;
}}
.stat-label {{
    color: {MUTED};
    font-size: 0.58rem;
    text-transform: uppercase;
    letter-spacing: 0.14em;
    margin-bottom: 0.32rem;
}}
.stat-value {{
    color: {TEXT};
    font-size: 1.35rem;
    font-weight: 600;
    letter-spacing: -0.02em;
}}
.hero-caption {{
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.22em;
    color: {ACCENT_DEEP};
    margin-bottom: 0.45rem;
}}
.section-label {{
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.18em;
    color: {ACCENT};
    margin: 1.5rem 0 0.6rem 0;
}}
[data-testid="stPlotlyChart"] {{
    background: linear-gradient(180deg, #15120f 0%, {SURFACE} 100%);
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 0.2rem;
    box-shadow: inset 0 1px 0 rgba(234, 88, 12, 0.06);
}}
</style>
"""

CHART_LAYOUT = dict(
    margin=dict(t=48, l=12, r=12, b=12),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color=TEXT, size=12, family="Segoe UI, system-ui, sans-serif"),
    title=dict(font=dict(size=13, color=ACCENT_DEEP), x=0, xanchor="left"),
)


def _layout(height=CHART_HEIGHT, **extra):
    return {**CHART_LAYOUT, "height": height, **extra}


def _apply_axes(fig, show_y_grid=False):
    fig.update_xaxes(
        showgrid=False,
        linecolor=BORDER,
        tickcolor=MUTED,
        tickfont=dict(color=MUTED, size=10),
    )
    fig.update_yaxes(
        showgrid=show_y_grid,
        gridcolor=BORDER,
        gridwidth=0.5,
        zeroline=False,
        linecolor=BORDER,
        tickcolor=MUTED,
        tickfont=dict(color=MUTED, size=10),
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


def _interpretation(profile) -> str:
    genres = profile.genre_weights.head(3).index.tolist()
    genre_phrase = " / ".join(genres)
    era = profile.era_buckets.idxmax() if not profile.era_buckets.empty else "mixed-era"
    top_genre = genres[0] if genres else "left-field electronics"
    return (
        f"The centre of gravity is {top_genre}: long-form, low-glare, late-night music. "
        f"The map pulls toward {genre_phrase}, mostly from the {era}, with a deep-cuts "
        f"index of {profile.obscurity_score}: more crate than chart."
    )


def _hero_title(profile) -> str:
    top_genre = profile.genre_weights.index[0] if not profile.genre_weights.empty else "Listening"
    return f"{top_genre.title()} at Low Light"


def _stat_strip(profile) -> str:
    return f"""
    <div class="stat-strip">
        <div class="stat">
            <div class="stat-label">Tracks mapped</div>
            <div class="stat-value">{profile.track_count}</div>
        </div>
        <div class="stat">
            <div class="stat-label">Avg popularity</div>
            <div class="stat-value">{profile.avg_popularity}</div>
        </div>
        <div class="stat">
            <div class="stat-label">Artists touched</div>
            <div class="stat-value">{profile.artist_count}</div>
        </div>
        <div class="stat">
            <div class="stat-label">Deep-cuts index</div>
            <div class="stat-value" style="color: {ACCENT_GLOW};">{profile.obscurity_score}</div>
        </div>
    </div>
    """


def _load_profile():
    uploaded = st.sidebar.file_uploader(
        "Use your own Exportify CSV",
        type=["csv"],
        help="Export Spotify liked songs or a playlist as CSV, then drop it here.",
    )

    if uploaded is not None:
        try:
            return analyze(load_csv(uploaded)), "Uploaded Spotify export"
        except Exception as exc:  # Streamlit should show parsing problems, not a blank page.
            st.sidebar.error(f"Could not read uploaded CSV: {exc}")

    if DEFAULT_CSV.exists():
        return analyze_file(DEFAULT_CSV), "Local liked songs export"

    if SAMPLE_CSV.exists():
        return analyze_file(SAMPLE_CSV), "Sample music export"

    st.error("No CSV found. Add a sample file or upload an Exportify CSV.")
    st.stop()


def genre_treemap(profile):
    weights = profile.genre_weights.head(TOP_GENRES)
    if weights.empty:
        return None

    genres = weights.index.tolist()
    counts = weights.values.tolist()
    colors = [GENRE_PALETTE[i % len(GENRE_PALETTE)] for i in range(len(genres))]

    fig = go.Figure(
        go.Treemap(
            labels=genres,
            parents=[""] * len(genres),
            values=counts,
            branchvalues="total",
            marker=dict(colors=colors, line=dict(color=BG, width=1.25)),
            textfont=dict(color=CREAM, size=12, family="Segoe UI, system-ui, sans-serif"),
            textinfo="label+value",
            insidetextfont=dict(color=CREAM, size=12),
            tiling=dict(pad=4),
        )
    )
    fig.update_layout(
        height=CHART_HEIGHT,
        margin=dict(t=48, l=8, r=8, b=8),
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        font=dict(color=TEXT, size=12, family="Segoe UI, system-ui, sans-serif"),
        title=dict(text="Genre composition", font=dict(size=13, color=ACCENT), x=0, xanchor="left"),
    )
    return fig


def era_bar(profile):
    buckets = profile.era_buckets
    if buckets.empty:
        return None

    values = buckets.values.tolist()
    fig = go.Figure(
        go.Bar(
            x=buckets.index.tolist(),
            y=values,
            marker=dict(color=_bar_fill_colors(values, "#172a2f", ACCENT), line=dict(width=0)),
        )
    )
    fig.update_layout(
        **_layout(
            paper_bgcolor=SURFACE,
            plot_bgcolor=SURFACE,
            xaxis_title=None,
            yaxis_title=None,
        )
    )
    fig.update_layout(title=dict(text="When the music was made", font=dict(size=13, color=MUTED), x=0, xanchor="left"))
    return _apply_axes(fig)


def top_artists_bar(profile, limit: int = 10):
    artists = profile.top_artists.head(limit)
    if artists.empty:
        return None

    values = artists.values.tolist()
    fig = go.Figure(
        go.Bar(
            x=values,
            y=artists.index.tolist(),
            orientation="h",
            marker=dict(color=_bar_fill_colors(values, "#162235", ACCENT), line=dict(width=0)),
        )
    )
    fig.update_layout(
        **_layout(
            height=SMALL_CHART_HEIGHT,
            paper_bgcolor=SURFACE,
            plot_bgcolor=SURFACE,
            yaxis=dict(categoryorder="total ascending"),
        )
    )
    fig.update_layout(title=dict(text=f"Top {limit} artists", font=dict(size=13, color=MUTED), x=0, xanchor="left"))
    return _apply_axes(fig)


st.set_page_config(page_title="Taste Map", layout="wide", page_icon="♪")

st.markdown(PAGE_CSS, unsafe_allow_html=True)

profile, source_label = _load_profile()

st.markdown(f'<p class="hero-caption">Taste Map / {source_label}</p>', unsafe_allow_html=True)
st.markdown(f'<p class="hero-title">{_hero_title(profile)}</p>', unsafe_allow_html=True)
st.markdown(f'<p class="hero-label">{profile.taste_label}</p>', unsafe_allow_html=True)
st.markdown(f'<p class="interpretation">{_interpretation(profile)}</p>', unsafe_allow_html=True)
st.markdown(_stat_strip(profile), unsafe_allow_html=True)

st.markdown('<p class="section-label">Composition</p>', unsafe_allow_html=True)
genre_fig = genre_treemap(profile)
if genre_fig is None:
    st.warning("No genre data in this export.")
else:
    st.plotly_chart(
        genre_fig,
        width="stretch",
        height=CHART_HEIGHT,
        theme=None,
        config={"displayModeBar": False, "responsive": True},
    )

st.markdown('<p class="section-label">Structure</p>', unsafe_allow_html=True)
left, right = st.columns(2)
with right:
    era_fig = era_bar(profile)
    if era_fig is None:
        st.warning("No release dates in this export.")
    else:
        st.plotly_chart(era_fig, width="stretch", theme=None, config={"displayModeBar": False})

with left:
    artists_fig = top_artists_bar(profile)
    if artists_fig is None:
        st.warning("No artist data in this export.")
    else:
        st.plotly_chart(artists_fig, width="stretch", theme=None, config={"displayModeBar": False})
