"""Load Exportify-style Spotify CSV exports and derive taste-map stats."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

# Column names we expect (Exportify); loader maps variants to these.
COL_TRACK = "track_name"
COL_ARTIST = "artist_names"
COL_RELEASE = "release_date"
COL_POPULARITY = "popularity"
COL_GENRES = "genres"

_COLUMN_ALIASES = {
    "track name": COL_TRACK,
    "artist name(s)": COL_ARTIST,
    "artist names": COL_ARTIST,
    "release date": COL_RELEASE,
    "popularity": COL_POPULARITY,
    "genres": COL_GENRES,
}


@dataclass
class TasteProfile:
    """Computed stats ready for charts and copy."""

    track_count: int
    genre_weights: pd.Series  # genre -> number of tracks tagged
    era_buckets: pd.Series  # decade label -> track count
    top_artists: pd.Series  # artist -> track count
    artist_count: int
    avg_popularity: float
    obscurity_score: float  # 100 - avg popularity (higher = deeper cuts)
    taste_label: str


def load_csv(path: str | Path) -> pd.DataFrame:
    """Read CSV and normalize column names."""
    df = pd.read_csv(path)
    rename = {}
    for col in df.columns:
        key = col.strip().lower()
        if key in _COLUMN_ALIASES:
            rename[col] = _COLUMN_ALIASES[key]
    df = df.rename(columns=rename)

    missing = {COL_TRACK, COL_ARTIST, COL_RELEASE, COL_GENRES} - set(df.columns)
    if missing:
        raise ValueError(f"CSV missing columns: {', '.join(sorted(missing))}")

    if COL_POPULARITY not in df.columns:
        df[COL_POPULARITY] = 0

    df[COL_POPULARITY] = pd.to_numeric(df[COL_POPULARITY], errors="coerce").fillna(0)
    df[COL_RELEASE] = pd.to_datetime(df[COL_RELEASE], errors="coerce")
    return df


def _split_list(value: object, sep: str) -> list[str]:
    if pd.isna(value) or not str(value).strip():
        return []
    return [part.strip() for part in str(value).split(sep) if part.strip()]


def _genre_weights(df: pd.DataFrame) -> pd.Series:
    rows: list[str] = []
    for raw in df[COL_GENRES]:
        rows.extend(_split_list(raw, ","))
    if not rows:
        return pd.Series(dtype=int)
    counts = pd.Series(rows).value_counts()
    return counts.sort_values(ascending=False)


def _era_buckets(df: pd.DataFrame) -> pd.Series:
    years = df[COL_RELEASE].dt.year.dropna().astype(int)
    if years.empty:
        return pd.Series(dtype=int)

    decades = (years // 10) * 10
    labels = decades.astype(str) + "s"
    return labels.value_counts().sort_index()


def _all_artists(df: pd.DataFrame) -> list[str]:
    rows: list[str] = []
    for raw in df[COL_ARTIST]:
        rows.extend(_split_list(raw, ";"))
    return rows


def _top_artists(df: pd.DataFrame, limit: int = 15) -> pd.Series:
    rows = _all_artists(df)
    if not rows:
        return pd.Series(dtype=int)
    return pd.Series(rows).value_counts().head(limit)


def _dominant_decade(era_buckets: pd.Series) -> str:
    if era_buckets.empty:
        return "mixed eras"
    decade = era_buckets.idxmax()
    return f"{decade}-leaning"


def _obscurity_tier(score: float) -> str:
    if score >= 65:
        return "deep-cut listener"
    if score >= 40:
        return "balanced crate-digger"
    return "mainstream-leaning"


def _taste_label(genre_weights: pd.Series, era_buckets: pd.Series, obscurity_score: float) -> str:
    if genre_weights.empty:
        return "Listening library portrait"

    top_genres = genre_weights.head(3).index.tolist()
    genre_phrase = " / ".join(top_genres)
    decade_phrase = _dominant_decade(era_buckets)
    tier = _obscurity_tier(obscurity_score)
    return f"{decade_phrase}, {genre_phrase}, {tier}"


def analyze(df: pd.DataFrame) -> TasteProfile:
    """Turn a normalized dataframe into chart-ready stats."""
    genre_weights = _genre_weights(df)
    era_buckets = _era_buckets(df)
    top_artists = _top_artists(df)
    artists = _all_artists(df)
    avg_popularity = float(df[COL_POPULARITY].mean())
    obscurity_score = round(100 - avg_popularity, 1)

    return TasteProfile(
        track_count=len(df),
        genre_weights=genre_weights,
        era_buckets=era_buckets,
        top_artists=top_artists,
        artist_count=len(set(artists)),
        avg_popularity=round(avg_popularity, 1),
        obscurity_score=obscurity_score,
        taste_label=_taste_label(genre_weights, era_buckets, obscurity_score),
    )


def analyze_file(path: str | Path) -> TasteProfile:
    return analyze(load_csv(path))


if __name__ == "__main__":
    default = Path(__file__).parent / "data" / "Liked_Songs.csv"
    profile = analyze_file(default)
    print(f"Tracks: {profile.track_count}")
    print(f"Label:  {profile.taste_label}")
    print(f"Obscurity score: {profile.obscurity_score} (avg popularity {profile.avg_popularity})")
    print("\nTop genres:")
    print(profile.genre_weights.head(8).to_string())
    print("\nEra buckets:")
    print(profile.era_buckets.to_string())
    print("\nTop artists:")
    print(profile.top_artists.head(8).to_string())
