# sauti-yetu — Voice of the People

A two-sided civic accountability platform built for the **Build with Gemma 4 Hackathon (GDG Pwani)**,
Track 1: *People's Priorities - AI for Constituency Development Planning*.

Citizens report issues in Swahili, Sheng, or English — by typing, recording a voice note, or
attaching a photo - from a chat-style input bar. Gemma 4 structures each report and powers:

1. **Public Portal** - a live dashboard of complaint hotspots by subcounty, drillable down to
   ward level (all 6 Mombasa subcounties, 30 official wards, common estate aliases); a
   "Responsiveness Clock" showing days unaddressed, sorted by urgency; a WhatsApp share link.
   Resolutions require admin evidence and sign-off, shown publicly, and any citizen can
   dispute a false "resolved" claim with a required reason.
2. **Admin Portal** - a gap detector clustering complaints by ward/category, a one-click
   NG-CDF funding proposal generator, evidence-required resolution with name + date
   sign-off, and an automatic SMS alert to the reporter the moment their issue is resolved.

## Live Demo

**https://sauti-yetu-6acxrivyrzexfj7dqemq8z.streamlit.app/**

Add `?admin=true` to the URL for the Admin Portal https://sauti-yetu-6acxrivyrzexfj7dqemq8z.streamlit.app/?admin=true
This is a lightweight route gate for demo purposes, not real authentication — see Known Limitations.

## Quick Start (local)

```powershell
git clone https://github.com/YOUR-USERNAME/sauti-yetu.git
cd sauti-yetu

python -m venv venv
venv\Scripts\activate

python -m pip install -r requirements.txt

Copy-Item .env.example .env
# Edit .env and add:
#   GOOGLE_API_KEY  (https://aistudio.google.com/apikey)
#   AT_USERNAME / AT_API_KEY  (https://account.africastalking.com) for SMS

streamlit run app.py
```

### Running without live API keys (mock mode)

If `GOOGLE_API_KEY` is unset, the app automatically falls back to a rule-based mock
classifier, so the full pipeline (structuring → storage → dashboard → CDF draft) is
testable offline. Mock mode cannot transcribe audio or interpret photos - a live key is
required for real multimodal understanding. SMS similarly falls back to a console-logged
mock if `AT_API_KEY` is unset.

### Loading the demo dataset

```powershell
python -c "import sys; sys.path.insert(0,'src'); import data_store as ds; ds.seed_from_csv('data/synthetic_complaints.csv')"
```

## Project Structure

```
sauti-yetu/
├── app.py                        # Streamlit app: Submit, Public Portal, Admin Portal
├── src/
│   ├── gemma_client.py           # All Gemma 4 calls: text/voice/photo classification
│   │                              # (function calling), CDF draft generation,
│   │                              # ward/subcounty mapping
│   ├── data_store.py             # CSV-backed pandas store: resolution status,
│   │                              # evidence, sign-off, and dispute tracking
│   └── sms_client.py             # Africa's Talking SMS integration for resolution alerts
├── data/
│   └── synthetic_complaints.csv  # Demo dataset (Swahili/Sheng/English, all Mombasa wards)
├── tests/
│   └── test_pipeline.py          # End-to-end pipeline tests
├── requirements.txt
├── .env.example
└── README.md
```

## How Gemma 4 Is Used

- **Native function calling** structures every complaint into
  `{category, urgency, ward, english_summary}` - one schema reused across text, voice, and photo.
- **Multimodal input** processes voice notes and photos directly, no separate
  speech-to-text or vision service.
- **Generation** drafts the formal NG-CDF proposal text from structured complaint clusters.

See kaggle.com/competitions/build-with-gemma-gdg-pwani/writeups/sauti-yetu for full architecture rationale, challenges, and technical tradeoffs.

## Known Limitations (by design, for a fast build)

- CSV/pandas store - no concurrency or durability guarantees.
- Admin route is gated by a URL query parameter, not real authentication.
- SMS sandbox (Africa's Talking) only delivers to Airtel test numbers; production tier needed for all networks.
- WhatsApp integration is a share link (`wa.me`), not full inbound Business API messaging - a roadmap item requiring Meta approval.
- No duplicate/spam detection on citizen submissions yet.
- Ward extraction in mock mode relies on a fixed known-wards list; live Gemma 4 handles free-text ward/subcounty names without this limitation.

## License

MIT
