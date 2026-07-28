"""
gemma_client.py

Wraps all Gemma 4 interactions for Sauti-Yetu:
  1. classify_complaint()        -> structures a raw citizen complaint into
                                    {category, urgency, ward, english_summary}
                                    using Gemma 4 native function calling.
  2. classify_complaint_audio()  -> processes voice notes directly.
  3. generate_cdf_draft()        -> generates a formal NG-CDF funding proposal
                                    from structured complaints.
"""

import os
import json
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GEMMA_MODEL = os.getenv("GEMMA_MODEL", "gemma-4-it")
FORCE_MOCK = os.getenv("FORCE_MOCK", "0") == "1"

CATEGORIES = ["Infrastructure", "Water", "Health", "Education", "Security", "Environment", "Other"]
URGENCY_LEVELS = ["High", "Medium", "Low"]

SYSTEM_PROMPT = """You are a civic-complaint structuring engine for a Kenyan constituency
development platform called Sauti-Yetu. Citizens write or speak complaints in Swahili,
Sheng, or English.

Your job: read the complaint and call the `structure_complaint` function with:
- category: the best-fitting category for the issue
- urgency: how urgent this is for residents' safety/wellbeing, not how angry the tone is
- ward: the ward, estate, or area name mentioned (if none, use "Unspecified")
- english_summary: a clear, neutral, one-sentence English summary suitable for an
  official document.

Be conservative with "High" urgency -- reserve it for safety, health, or water access risks."""

_STRUCTURE_COMPLAINT_SCHEMA = {
    "name": "structure_complaint",
    "description": "Structures a raw citizen complaint into a standard record.",
    "parameters": {
        "type": "object",
        "properties": {
            "category": {"type": "string", "enum": CATEGORIES},
            "urgency": {"type": "string", "enum": URGENCY_LEVELS},
            "ward": {"type": "string"},
            "english_summary": {"type": "string"},
        },
        "required": ["category", "urgency", "ward", "english_summary"],
    },
}

_KNOWN_WARDS = [
    # 6 Sub-Counties / Constituencies
    "Changamwe", "Jomvu", "Kisauni", "Nyali", "Likoni", "Mvita",

    # 30 Official Electoral Wards
    "Port Reitz", "Kipevu", "Airport", "Chaani",
    "Jomvu Kuu", "Miritini", "Mikindani",
    "Mjambere", "Junda", "Bamburi", "Mwakirunge", "Mtopanga", "Magogoni", "Shanzu",
    "Frere Town", "Ziwa la Ng'ombe", "Mkomani", "Kongowea", "Kadzandani",
    "Mtongwe", "Shika Adabu", "Bofu", "Timbwani",
    "Mji wa Kale", "Makadara", "Tudor", "Tononoka", "Majengo", "Ganjoni", "Shimanzi",

    # Common Local Estates & Neighborhoods (Fallback Aliases)
    "Bombolulu", "Mwembe Tayari", "Old Town", "Maweni", "Kizingo", "Magongo",
]

# Sorted longest-first so a specific ward (e.g. "Jomvu Kuu") matches before
# its shorter subcounty name (e.g. "Jomvu") -- prevents losing specificity.
_KNOWN_WARDS_SORTED = sorted(_KNOWN_WARDS, key=len, reverse=True)
_TRANSLATION_HINTS = {
    "barabara": "road", "zimeharibika": "damaged", "gari": "vehicles",
    "hazipiti": "cannot pass", "wiki": "week(s)", "moshi": "smoke",
    "kiwanda": "factory", "watoto": "children", "maji": "water",
    "hatuna": "we have no", "taka": "garbage", "harufu": "smell",
    "mbaya": "bad", "mbu": "mosquitoes", "hospitali": "hospital",
    "dawa": "medicine", "shule": "school", "choo": "toilet",
    "wanaumia": "are suffering", "wizi": "theft", "hakuna": "there is no",
    "doria": "patrol", "usiku": "at night", "hatari": "dangerous",
    "kunywa": "to drink", "safi": "clean", "daraja": "bridge",
    "limebomoka": "has partially collapsed",
}


def _get_client():
    """Lazily create the genai client. Returns None if unavailable -> triggers mock mode."""
    if FORCE_MOCK or not GOOGLE_API_KEY:
        return None
    try:
        from google import genai
        return genai.Client(api_key=GOOGLE_API_KEY)
    except Exception as e:
        print(f"[gemma_client] Could not init Gemma client, falling back to mock mode: {e}")
        return None


def _extract_ward(text: str) -> str:
    for ward in _KNOWN_WARDS_SORTED:
        if ward.lower() in text.lower():
            return ward
    return "Unspecified"


def _rough_translate(text: str) -> str:
    words = text.split()
    translated = [_TRANSLATION_HINTS.get(w.strip(".,!").lower(), w) for w in words]
    return " ".join(translated)[:200]


def _mock_classify(raw_text: str) -> dict:
    """Rule-based stand-in for Gemma 4, used when there's no live API access."""
    text_lower = raw_text.lower()

    if any(w in text_lower for w in ["maji", "water", "kisima", "sewage"]):
        category = "Water"
    elif any(w in text_lower for w in ["barabara", "road", "gari", "daraja", "bridge", "pothole"]):
        category = "Infrastructure"
    elif any(w in text_lower for w in ["hospitali", "health", "dawa", "clinic"]):
        category = "Health"
    elif any(w in text_lower for w in ["shule", "school"]):
        category = "Education"
    elif any(w in text_lower for w in ["wizi", "usalama", "security", "theft", "unsafe"]):
        category = "Security"
    elif any(w in text_lower for w in ["taka", "uchafu", "dump", "pollution", "moshi", "air quality"]):
        category = "Environment"
    else:
        category = "Other"

    if any(w in text_lower for w in ["haraka", "hatari", "danger", "emergency", "wiki mbili", "kila siku"]):
        urgency = "High"
    elif any(w in text_lower for w in ["polepole", "eventually", "not urgent", "sometime"]):
        urgency = "Low"
    else:
        urgency = "Medium"

    return {
        "category": category,
        "urgency": urgency,
        "ward": _extract_ward(raw_text),
        "english_summary": _rough_translate(raw_text),
    }


def classify_complaint(raw_text: str) -> dict:
    client = _get_client()
    result = None

    if client is not None:
        try:
            from google.genai import types

            tool = types.Tool(function_declarations=[
                types.FunctionDeclaration(**_STRUCTURE_COMPLAINT_SCHEMA)
            ])
            config = types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                tools=[tool],
                tool_config=types.ToolConfig(
                    function_calling_config=types.FunctionCallingConfig(mode="ANY")
                ),
            )
            response = client.models.generate_content(
                model=GEMMA_MODEL,
                contents=raw_text,
                config=config,
            )
            call = response.candidates[0].content.parts[0].function_call
            result = dict(call.args)
        except Exception as e:
            print(f"[gemma_client] Live classify_complaint call failed, using mock: {e}")
            result = None

    if result is None:
        result = _mock_classify(raw_text)

    result["timestamp"] = datetime.now(timezone.utc).isoformat()
    result["raw_text"] = raw_text
    result["days_unresolved"] = 0
    return result


def classify_complaint_audio(audio_path: str) -> dict:
    client = _get_client()
    if client is None:
        return _mock_classify("[audio input -- mock mode has no transcription]")

    try:
        from google.genai import types

        uploaded = client.files.upload(file=audio_path)
        tool = types.Tool(function_declarations=[
            types.FunctionDeclaration(**_STRUCTURE_COMPLAINT_SCHEMA)
        ])
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=[tool],
            tool_config=types.ToolConfig(
                function_calling_config=types.FunctionCallingConfig(mode="ANY")
            ),
        )
        response = client.models.generate_content(
            model=GEMMA_MODEL,
            contents=[uploaded],
            config=config,
        )
        call = response.candidates[0].content.parts[0].function_call
        result = dict(call.args)
    except Exception as e:
        print(f"[gemma_client] Live audio classify failed, using mock: {e}")
        result = _mock_classify("[audio input -- fallback mock]")

    result["timestamp"] = datetime.now(timezone.utc).isoformat()
    result["raw_text"] = f"[voice note: {os.path.basename(audio_path)}]"
    result["days_unresolved"] = 0
    return result

def classify_complaint_image(image_path: str) -> dict:
    """
    Same idea as classify_complaint_audio(), but for a photo. Gemma 4's
    multimodal understanding reads the image directly -- e.g. a pothole,
    an overflowing dumpsite, a burst pipe -- and structures it the same
    way as a text or voice complaint.
    """
    client = _get_client()
    if client is None:
        return _mock_classify("[photo input -- mock mode has no image understanding]")

    try:
        from google.genai import types

        uploaded = client.files.upload(file=image_path)
        tool = types.Tool(function_declarations=[
            types.FunctionDeclaration(**_STRUCTURE_COMPLAINT_SCHEMA)
        ])
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT + (
                "\n\nThe citizen has attached a photo instead of writing a description. "
                "Look at the photo and infer the category, urgency, and a clear "
                "english_summary describing what the photo shows. If no ward/location "
                "is visible or inferable, use 'Unspecified'."
            ),
            tools=[tool],
            tool_config=types.ToolConfig(
                function_calling_config=types.FunctionCallingConfig(mode="ANY")
            ),
        )
        response = client.models.generate_content(
            model=GEMMA_MODEL,
            contents=[uploaded],
            config=config,
        )
        call = response.candidates[0].content.parts[0].function_call
        result = dict(call.args)
    except Exception as e:
        print(f"[gemma_client] Live photo classify failed, using mock: {e}")
        result = _mock_classify("[photo input -- fallback mock]")

    result["timestamp"] = datetime.now(timezone.utc).isoformat()
    result["raw_text"] = f"[photo report: {os.path.basename(image_path)}]"
    result["days_unresolved"] = 0
    return result


def _mock_cdf_draft(complaints_df) -> str:
    ward = complaints_df["ward"].mode().iloc[0] if not complaints_df.empty else "Unspecified"
    category = complaints_df["category"].mode().iloc[0] if not complaints_df.empty else "Infrastructure"
    count = len(complaints_df)
    summaries = "\n".join(f"- {s}" for s in complaints_df["english_summary"].head(5))
    return f"""NG-CDF FUNDING PROPOSAL (DRAFT)

To: National Government Constituencies Development Fund Committee
Ward: {ward}
Category: {category}
Date: {datetime.now(timezone.utc).strftime('%d %B %Y')}

SUBJECT: Request for Funding -- {category} Interventions in {ward} Ward

1. BACKGROUND
This proposal is generated from {count} citizen-reported complaint(s) received through the
Sauti-Yetu public reporting platform, indicating a sustained {category.lower()} issue
affecting residents of {ward} ward.

2. CITIZEN-REPORTED EVIDENCE
{summaries}

3. REQUEST
The committee is requested to review and allocate funding under the applicable NG-CDF
category to address the issue(s) described above, given their direct impact on resident
safety and wellbeing.

4. NEXT STEPS
A site assessment by the relevant technical officer is recommended prior to fund disbursement.

[This is an auto-generated draft. It requires review and formal sign-off before submission.]"""


def generate_cdf_draft(complaints_df) -> str:
    client = _get_client()
    if client is None or complaints_df.empty:
        return _mock_cdf_draft(complaints_df)

    try:
        records = complaints_df[["category", "ward", "urgency", "english_summary"]].to_dict("records")
        prompt = (
            "Using the citizen complaint records below, draft a formal NG-CDF funding "
            "proposal addressed to the National Government Constituencies Development Fund "
            "Committee. Use a professional tone suitable for a government document. Include "
            "sections: Background, Citizen-Reported Evidence, Request, Next Steps.\n\n"
            f"Records:\n{json.dumps(records, indent=2)}"
        )
        response = client.models.generate_content(model=GEMMA_MODEL, contents=prompt)
        return response.text
    except Exception as e:
        print(f"[gemma_client] Live CDF draft generation failed, using mock: {e}")
        return _mock_cdf_draft(complaints_df)