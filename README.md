# sauti-yetu — Voice of the People

A two-sided civic accountability platform built for the **Build with Gemma 4 Hackathon (GDG Pwani)**,
Track 1: *People's Priorities — AI for Constituency Development Planning*.

Citizens report issues in Swahili, Sheng, or English — by typing, recording a voice note, or
attaching a photo. Gemma 4 structures each report and powers two things:

1. **Public Portal** — a hotspot table with a "Responsiveness Clock" showing how long each
   issue has gone unaddressed, plus evidence-required resolution with a community dispute
   button, so a false "resolved" claim can be challenged.
2. **Admin Portal** — a gap detector clustering complaints by ward/category, a one-click
   NG-CDF funding proposal generator, and a sign-off flow (name + date) for accountability
   on every resolution.

## Quick Start

\`\`\`powershell
git clone https://github.com/YOUR-USERNAME/sauti-yetu.git
cd sauti-yetu

python -m venv venv
venv\Scripts\activate

pip install -r requirements.txt

Copy-Item .env.example .env
# Edit .env and add your GOOGLE_API_KEY (https://aistudio.google.com/apikey)

streamlit run app.py
\`\`\`

Runs in mock mode automatically if no API key is set — useful for offline testing.

## How Gemma 4 Is Used

- **Native function calling** structures every complaint (text, voice, or photo) into
  `{category, urgency, ward, english_summary}`.
- **Multimodal input** processes voice notes and photos directly, no separate
  transcription/vision step.
- **Generation** drafts the formal NG-CDF proposal text from clustered complaints.

## Known Limitations (by design, for a fast build)

- CSV/pandas store — no concurrency guarantees.
- No authentication.
- Full WhatsApp Business API integration (inbound messaging) is a roadmap item —
  the current build uses a WhatsApp share link instead.