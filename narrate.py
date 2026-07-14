"""Template and optional LLM portraits from a taste brief."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from enum import Enum

from parse import TasteProfile


class StoryAngle(str, Enum):
    DEEP_WARREN = "deep_warren"
    ERA_LOCKED = "era_locked"
    GENRE_SCATTER = "genre_scatter"
    ARTIST_ANCHORED = "artist_anchored"
    MOOD_LED = "mood_led"
    MAINSTREAM_ADJACENT = "mainstream_adjacent"


@dataclass
class Portrait:
    title: str
    label: str
    interpretation: str
    source: str = "template"


def _top_genres_list(brief: dict, limit: int = 3) -> list[str]:
    shares = brief.get("genre_shares_top5") or {}
    return list(shares.keys())[:limit]


def _genre_phrase(brief: dict, limit: int = 3) -> str:
    genres = _top_genres_list(brief, limit)
    if not genres:
        return "a wide mix of sounds"
    if len(genres) == 1:
        return genres[0]
    if len(genres) == 2:
        return f"{genres[0]} and {genres[1]}"
    return f"{genres[0]}, {genres[1]}, and {genres[2]}"


def _genre_title(brief: dict) -> str:
    top = brief.get("top_genre")
    return top.title() if top else "Listening"


def _is_bright(brief: dict) -> bool:
    mood = brief.get("mood") or {}
    energy = mood.get("energy")
    valence = mood.get("valence")
    if energy is None or valence is None:
        return False
    return energy >= 0.6 and valence >= 0.55


def _is_quiet(brief: dict) -> bool:
    mood = brief.get("mood") or {}
    energy = mood.get("energy")
    valence = mood.get("valence")
    if energy is None:
        return False
    if energy < 0.45:
        return True
    return energy < 0.5 and (valence or 0.5) < 0.4


def _pick_story_angle(profile: TasteProfile, brief: dict) -> StoryAngle:
    s = profile.stats
    mood = brief.get("mood") or {}

    if profile.obscurity_score < 40:
        return StoryAngle.MAINSTREAM_ADJACENT

    if s.mood_contrast and mood.get("contrast"):
        contrast_lower = s.mood_contrast.lower()
        distinct_mood = _is_bright(brief) or _is_quiet(brief) or any(
            phrase in contrast_lower
            for phrase in ("inward", "kinetic but", "bright and", "quiet and", "soft but")
        )
        if distinct_mood:
            return StoryAngle.MOOD_LED

    if s.top_artist_share_pct >= 8:
        return StoryAngle.ARTIST_ANCHORED

    if brief.get("era_outlier") or s.top_era_share_pct >= 45:
        return StoryAngle.ERA_LOCKED

    if profile.obscurity_score >= 65:
        return StoryAngle.DEEP_WARREN

    if brief.get("genre_scattered"):
        return StoryAngle.GENRE_SCATTER

    return StoryAngle.ERA_LOCKED


def _depth_tag(profile: TasteProfile) -> str:
    if profile.obscurity_score >= 65:
        return "Off the Algorithm"
    if profile.obscurity_score >= 40:
        return "Beyond the Charts"
    return "Chart Favorites"


def _title_for_angle(angle: StoryAngle, profile: TasteProfile, brief: dict) -> str:
    genre = _genre_title(brief)
    era = brief.get("top_era")
    artist = brief.get("top_artist")
    depth = _depth_tag(profile)

    if angle == StoryAngle.MAINSTREAM_ADJACENT:
        if era:
            return f"{era} {genre}, Chart Favorites"
        return f"{genre} on Repeat"

    if angle == StoryAngle.MOOD_LED:
        if _is_bright(brief):
            return f"{genre} in Full Color"
        if _is_quiet(brief):
            return f"{genre} at Low Light"
        return f"{genre}, Steady Motion"

    if angle == StoryAngle.GENRE_SCATTER:
        return f"Wide Lens, {era} Center" if era else "A Scattered Library"

    if angle == StoryAngle.ARTIST_ANCHORED:
        if artist:
            return f"{artist} and {genre}"
        return f"{genre} on Repeat"

    if angle == StoryAngle.ERA_LOCKED and era:
        return f"{era} {genre}, {depth}"

    if profile.obscurity_score >= 65:
        return f"{genre} in the Margins"

    if _is_bright(brief):
        return f"{genre} in Full Color"
    if _is_quiet(brief):
        return f"{genre} at Low Light"
    return f"{era} {genre}, {depth}" if era else f"{genre}, {depth}"


def _secondary_genres_clause(brief: dict) -> str:
    genres = _top_genres_list(brief, 3)
    if len(genres) < 2:
        return ""
    second = genres[1].title()
    if len(genres) == 2:
        return f"{second} broadens the core"
    third = genres[2].title()
    return f"{second} and {third} broaden the core"


def _depth_clause(profile: TasteProfile) -> str:
    if profile.obscurity_score >= 65:
        return "Popularity stays low across the playlist, away from the current mainstream."
    if profile.obscurity_score >= 40:
        return "Popularity sits near the middle of Spotify's scale."
    return "Popularity runs high on Spotify's scale."


def _supporting_detail(angle: StoryAngle, profile: TasteProfile, brief: dict) -> str:
    """One additional observation that does not repeat the lead angle."""
    s = profile.stats

    if angle != StoryAngle.ERA_LOCKED and s.era_span_decades >= 4:
        return f"The release dates span {s.era_span_decades} decades."

    if (
        angle != StoryAngle.ARTIST_ANCHORED
        and s.top_artist
        and s.top_artist_share_pct >= 8
    ):
        return f"{s.top_artist} is the most frequently repeated artist in the selection."

    if angle != StoryAngle.GENRE_SCATTER and s.top_genre_share_pct < 15:
        return "No one style carries much of the overall weight."

    if angle != StoryAngle.ARTIST_ANCHORED and s.tracks_per_artist <= 1.5:
        return "Most artists appear only once or twice."

    return ""


def _interpretation_for_angle(
    angle: StoryAngle, profile: TasteProfile, brief: dict
) -> str:
    era = brief.get("top_era")
    artist = brief.get("top_artist")
    mood = brief.get("mood") or {}
    secondary = _secondary_genres_clause(brief)
    depth = _depth_clause(profile)
    supporting = _supporting_detail(angle, profile, brief)

    if angle == StoryAngle.ERA_LOCKED and era:
        if secondary:
            lead = f"{secondary}, while the {era} account for the largest share of the tracks."
        elif brief.get("top_era_share_pct", 0):
            lead = f"The {era} account for the largest share of the tracks."
        else:
            lead = f"The release dates center on the {era}."
        return " ".join(part for part in (lead, depth, supporting) if part)

    if angle == StoryAngle.DEEP_WARREN:
        genres = _genre_phrase(brief, 2)
        return " ".join(
            part for part in (f"{genres.title()} are the clearest musical thread.", depth, supporting) if part
        )

    if angle == StoryAngle.GENRE_SCATTER:
        genres = _genre_phrase(brief, 3)
        era_bit = f", with the {era} as the anchor decade" if era else ""
        return " ".join(
            part
            for part in (
                f"No genre dominates: {genres} are the strongest strands{era_bit}.",
                depth,
                supporting,
            )
            if part
        )

    if angle == StoryAngle.ARTIST_ANCHORED and artist:
        count = brief.get("top_artist_tracks")
        if count:
            lead = f"{artist} appears {count} times, more than any other artist."
        else:
            lead = f"{artist} appears more often than any other artist."
        return " ".join(part for part in (lead, depth, supporting) if part)

    if angle == StoryAngle.MOOD_LED:
        contrast = mood.get("contrast")
        if _is_bright(brief):
            lead = "The tracks are generally bright and high-energy."
        elif _is_quiet(brief):
            lead = "The tracks are generally low-energy and subdued."
        elif contrast:
            lead = f"The mood is {contrast.lower()}."
        else:
            lead = "The audio features point to a consistent mood."
        return " ".join(part for part in (lead, depth, supporting) if part)

    if angle == StoryAngle.MAINSTREAM_ADJACENT:
        genres = _genre_phrase(brief, 2)
        return " ".join(
            part
            for part in (
                f"{genres.title()} lead a relatively high-popularity selection.",
                depth,
                supporting,
            )
            if part
        )

    genres = _genre_phrase(brief, 2)
    return " ".join(part for part in (f"{genres.title()} are the dominant sounds here.", depth, supporting) if part)


def template_portrait(profile: TasteProfile, brief: dict) -> Portrait:
    """Editorial copy from computed stats — natural language, not stat chains."""
    angle = _pick_story_angle(profile, brief)
    return Portrait(
        title=_title_for_angle(angle, profile, brief),
        label="",
        interpretation=_interpretation_for_angle(angle, profile, brief),
        source="template",
    )


def template_library_summary(summary: dict) -> str:
    """Brief cross-playlist overview — editorial, not a table."""
    if not summary:
        return ""

    n = summary["playlist_count"]
    tracks = summary["total_tracks"]
    lead = f"{n} playlists · {tracks:,} tracks. "

    common_genre = summary.get("common_genre")
    common_era = summary.get("common_era")
    common_count = summary.get("common_genre_count", 0)

    if common_genre and common_count >= 2:
        thread = f"{common_genre.title()} is the common thread"
        if common_era and common_count >= n // 2 + 1:
            thread += f", with the {common_era} appearing most often"
        lead += thread + ". "
    elif common_era:
        lead += f"The {common_era} are the most common release period. "

    extras: list[str] = []

    outlier = summary.get("outlier_name")
    outlier_genre = summary.get("outlier_genre")
    outlier_era = summary.get("outlier_era")
    if outlier and outlier_genre:
        era_bit = f", {outlier_era}" if outlier_era and outlier_era != common_era else ""
        extras.append(f"{outlier} is the outlier ({outlier_genre}{era_bit})")

    quietest = summary.get("quietest")
    brightest = summary.get("brightest")
    if quietest and brightest and quietest != brightest:
        extras.append(f"{quietest} has the lowest energy; {brightest} the highest positivity")
    elif quietest:
        extras.append(f"{quietest} has the lowest energy")
    elif brightest:
        extras.append(f"{brightest} has the highest positivity")

    mainstream = summary.get("mainstream_name")
    if (
        mainstream
        and summary.get("mainstream_deep_cuts", 100) < 60
        and mainstream != outlier
    ):
        extras.append(f"{mainstream} has the highest average popularity")

    if extras:
        lead += ". ".join(extras) + "."

    if summary.get("avg_deep_cuts", 0) >= 70:
        lead = lead.rstrip() + " Across the collection, average popularity remains low."

    return lead.strip()


def llm_configured(groq_api_key: str | None, ollama_model: str | None) -> bool:
    return bool(groq_api_key or ollama_model)


def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def _chat_complete(messages: list[dict], groq_api_key: str | None, ollama_model: str | None) -> tuple[str, str]:
    """Returns (body, provider name)."""
    if groq_api_key:
        payload = json.dumps(
            {
                "model": "llama-3.3-70b-versatile",
                "messages": messages,
                "temperature": 0.6,
                "max_tokens": 320,
            }
        ).encode()
        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {groq_api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = json.loads(resp.read().decode())
        return data["choices"][0]["message"]["content"], "groq"

    assert ollama_model
    payload = json.dumps(
        {"model": ollama_model, "messages": messages, "stream": False}
    ).encode()
    req = urllib.request.Request(
        "http://localhost:11434/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode())
    return data["message"]["content"], "ollama"


_AI_SYSTEM_PROMPT = """You write short editorial music taste portraits — like a caption in a well-edited magazine, not a dashboard summary.

Use ONLY the facts in the playlist brief. Do not invent tracks, artists, or numbers.

Return valid JSON only:
{"title": "...", "label": "...", "interpretation": "..."}

Voice rules:
- Title: one 5–8 word display headline that combines era, lead genre, and listening character (e.g. "2010s Organic House, Off the Algorithm").
- Label: leave as an empty string unless a single short subline truly adds something the title cannot.
- Interpretation: two short sentences; add a third only when it introduces a separate fact. Do not pad with lifestyle language or a summary of the title.
- State relative popularity plainly. Never contrast discovering music with streaming it, or imply a track's popularity explains how it is played.
- Do not weaken a claim with a self-qualifier such as "only part of the picture."

Forbidden phrases: "decade-first listening", "era sets the frame", "genre follows the decade", "genre tags", "distinct genres", "tracks sit in", "deep-cuts index", "digs, not streams", "more discovery than comfort", "built for browsing", "X% of genre", "appears most (".

Example A (quiet electronic):
{"title": "2010s Ambient, Off the Algorithm", "label": "", "interpretation": "Downtempo and IDM extend an ambient center. The 2010s account for the largest share of the tracks. Popularity stays low across the playlist, away from the current mainstream."}

Example B (bright dance):
{"title": "Disco House in Full Color", "label": "", "interpretation": "The audio features are bright and high-energy. Afropop and nu disco are the strongest secondary styles. Popularity sits near the middle of Spotify's scale."}
"""


def ai_portrait(
    brief: dict,
    groq_api_key: str | None = None,
    ollama_model: str | None = None,
) -> Portrait | None:
    """Optional LLM portrait. Returns None on missing config or failure."""
    if not llm_configured(groq_api_key, ollama_model):
        return None

    user = f"Playlist facts:\n{json.dumps(brief, indent=2)}"
    messages = [{"role": "system", "content": _AI_SYSTEM_PROMPT}, {"role": "user", "content": user}]

    try:
        raw, provider = _chat_complete(messages, groq_api_key, ollama_model)
        parsed = _extract_json(raw)
        return Portrait(
            title=str(parsed["title"]).strip(),
            label=str(parsed["label"]).strip(),
            interpretation=str(parsed["interpretation"]).strip(),
            source=provider,
        )
    except (urllib.error.URLError, urllib.error.HTTPError, KeyError, json.JSONDecodeError, TimeoutError):
        return None
