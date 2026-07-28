"""
data_store.py

Lightweight CSV-backed pandas store for structured complaints, including
resolution status with evidence, admin sign-off, and community disputes.
"""

import os
import uuid
from datetime import datetime, timezone

import pandas as pd

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "complaints.csv")

COLUMNS = [
    "id", "category", "urgency", "ward", "english_summary", "raw_text", "timestamp",
    "phone", "status", "resolution_note", "resolution_photo",
    "resolved_by", "resolved_date", "dispute_count", "dispute_reasons",
]

_STR_COLS = [
    "id", "category", "urgency", "ward", "english_summary", "raw_text",
    "phone", "status", "resolution_note", "resolution_photo",
    "resolved_by", "resolved_date", "dispute_reasons",
]


def _ensure_store():
    if not os.path.exists(DATA_PATH):
        pd.DataFrame(columns=COLUMNS).to_csv(DATA_PATH, index=False)


def _coerce_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """Forces columns to consistent types -- CSV round-trips turn blank
    strings into NaN/float, which then blocks writing real text back in."""
    if "id" not in df.columns:
        df["id"] = [str(uuid.uuid4())[:8] for _ in range(len(df))]

    for col in _STR_COLS:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].fillna("").astype(str)

    df["id"] = df["id"].apply(lambda v: v if v else str(uuid.uuid4())[:8])
    if "status" in df.columns:
        df["status"] = df["status"].replace("", "Open")

    df["dispute_count"] = (
        pd.to_numeric(df["dispute_count"], errors="coerce").fillna(0).astype(int)
        if "dispute_count" in df.columns else 0
    )
    return df


def load_complaints() -> pd.DataFrame:
    _ensure_store()
    df = pd.read_csv(DATA_PATH)
    if df.empty:
        return df

    df = _coerce_dtypes(df)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, format="ISO8601")    
    now = datetime.now(timezone.utc)
    df["days_unresolved"] = (now - df["timestamp"]).dt.days
    df.to_csv(DATA_PATH, index=False)  # persist any backfilled columns/ids

    return df.sort_values(by=["status", "urgency", "days_unresolved"], ascending=[True, True, False])


def add_complaint(record: dict) -> None:
    _ensure_store()
    record = dict(record)
    record.setdefault("id", str(uuid.uuid4())[:8])
    record.setdefault("phone", "")
    record.setdefault("status", "Open")
    record.setdefault("resolution_note", "")
    record.setdefault("resolution_photo", "")
    record.setdefault("resolved_by", "")
    record.setdefault("resolved_date", "")
    record.setdefault("dispute_count", 0)
    record.setdefault("dispute_reasons", "")
    row = {k: record.get(k, "") for k in COLUMNS}
    df = pd.read_csv(DATA_PATH) if os.path.getsize(DATA_PATH) > 0 else pd.DataFrame(columns=COLUMNS)
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv(DATA_PATH, index=False)


def seed_from_csv(seed_path: str) -> int:
    """Loads a synthetic seed dataset into the store. Returns number of rows added."""
    _ensure_store()
    seed_df = pd.read_csv(seed_path)
    if "id" not in seed_df.columns:
        seed_df["id"] = [str(uuid.uuid4())[:8] for _ in range(len(seed_df))]
    defaults = {
        "phone": "", "status": "Open", "resolution_note": "", "resolution_photo": "",
        "resolved_by": "", "resolved_date": "", "dispute_count": 0, "dispute_reasons": "",
    }
    for col, default in defaults.items():
        if col not in seed_df.columns:
            seed_df[col] = default
    seed_df = seed_df[[c for c in COLUMNS if c in seed_df.columns]]
    existing = pd.read_csv(DATA_PATH) if os.path.getsize(DATA_PATH) > 0 else pd.DataFrame(columns=COLUMNS)
    combined = pd.concat([existing, seed_df], ignore_index=True)
    combined.to_csv(DATA_PATH, index=False)
    return len(seed_df)


def mark_resolved(complaint_id: str, note: str, resolved_by: str, photo_path: str = "", resolved_date: str = None) -> dict:
    """Admin marks a complaint resolved with required evidence + sign-off.
    Returns the resolved row (used to trigger an SMS alert if a phone was given)."""
    df = pd.read_csv(DATA_PATH)
    df = _coerce_dtypes(df)
    idx = df.index[df["id"] == complaint_id]
    if len(idx) == 0:
        raise ValueError(f"No complaint found with id {complaint_id}")

    resolved_date = resolved_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    df.loc[idx, "status"] = "Resolved"
    df.loc[idx, "resolution_note"] = note
    df.loc[idx, "resolution_photo"] = photo_path
    df.loc[idx, "resolved_by"] = resolved_by
    df.loc[idx, "resolved_date"] = resolved_date
    df.loc[idx, "dispute_count"] = 0
    df.loc[idx, "dispute_reasons"] = ""
    df.to_csv(DATA_PATH, index=False)
    return df.loc[idx].iloc[0].to_dict()


def dispute_resolution(complaint_id: str, reason: str, reopen_threshold: int = 2) -> None:
    """A citizen disputes a resolved complaint with a required reason.
    Reopens (marks Disputed) once enough disputes come in."""
    df = pd.read_csv(DATA_PATH)
    df = _coerce_dtypes(df)
    idx = df.index[df["id"] == complaint_id]
    if len(idx) == 0:
        raise ValueError(f"No complaint found with id {complaint_id}")

    existing_reasons = df.loc[idx, "dispute_reasons"].iloc[0]
    combined_reasons = f"{existing_reasons} | {reason}" if existing_reasons else reason
    df.loc[idx, "dispute_reasons"] = combined_reasons
    df.loc[idx, "dispute_count"] = df.loc[idx, "dispute_count"].astype(int) + 1
    if df.loc[idx, "dispute_count"].iloc[0] >= reopen_threshold:
        df.loc[idx, "status"] = "Disputed"
    df.to_csv(DATA_PATH, index=False)