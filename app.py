"""
Sauti-Yetu -- Streamlit app
Public Portal (citizen accountability) + Admin Portal (CDF draft generator)
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import streamlit as st
import pandas as pd

import gemma_client as gc
import data_store as ds
import sms_client as sms

if gc.FORCE_MOCK or not gc.GOOGLE_API_KEY:
    st.sidebar.warning("⚠️ Running in MOCK mode — no live Gemma 4 connection")
else:
    st.sidebar.success("✅ Live Gemma 4 connected")

st.set_page_config(page_title="Sauti-Yetu", page_icon="📣", layout="wide")

st.title("📣 Sauti-Yetu")
st.caption("Voice of the People — turning citizen complaints into constituency action, powered by Gemma 4.")

is_admin = st.query_params.get("admin", "false") == "true"

if is_admin:
    tab_public, tab_admin, tab_submit = st.tabs(["🌍 Public Portal", "🏛️ Admin Portal", "📝 Submit a Report"])
else:
    tab_public, tab_submit = st.tabs(["🌍 Public Portal", "📝 Submit a Report"])
    tab_admin = None

# ---------------------------------------------------------------------------
# SUBMIT TAB -- chat-style input: text, mic, or photo
# ---------------------------------------------------------------------------
with tab_submit:
    st.subheader("Submit a community issue")
    st.write("Type, speak, or attach a photo — Swahili, Sheng, or English, Gemma 4 handles the rest.")

    raw_text = st.text_input("Type a message", placeholder="e.g. Kuna moshi mzito Changamwe...")
    phone = st.text_input("Phone number (optional — get an SMS when this is resolved)", placeholder="07XXXXXXXX")
    ward_choice = st.selectbox("Select your ward or subcounty", sorted(gc._KNOWN_WARDS))

    col_mic, col_photo = st.columns(2)

    with col_mic:
        st.markdown("🎙️ **Or record a voice note**")
        recorded_audio = st.audio_input("Tap to record")

    with col_photo:
        st.markdown("📎 **Or attach a photo**")
        photo_source = st.radio("Photo source", ["Camera", "Upload"], horizontal=True, label_visibility="collapsed")
        if photo_source == "Camera":
            attached_photo = st.camera_input("Take a photo", label_visibility="collapsed")
        else:
            attached_photo = st.file_uploader("Upload a photo", type=["jpg", "jpeg", "png"], label_visibility="collapsed")

    if st.button("Send report", type="primary"):
        if recorded_audio is not None:
            os.makedirs("data", exist_ok=True)
            tmp_path = os.path.join("data", "_tmp_voice.wav")
            with open(tmp_path, "wb") as f:
                f.write(recorded_audio.getbuffer())
            with st.spinner("Gemma 4 is processing your voice note..."):
                record = gc.classify_complaint_audio(tmp_path)
                record["phone"] = phone.strip()
                record["ward"] = ward_choice
                ds.add_complaint(record)
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            st.success(f"Logged as **{record['category']}** ({record['urgency']} urgency) — {record['ward']}")

        elif attached_photo is not None:
            tmp_path = os.path.join("data", "_tmp_photo.jpg")
            with open(tmp_path, "wb") as f:
                f.write(attached_photo.getbuffer())
            with st.spinner("Gemma 4 is looking at your photo..."):
                record = gc.classify_complaint_image(tmp_path)
                record["phone"] = phone.strip()
                record["ward"] = ward_choice
                ds.add_complaint(record)
            os.remove(tmp_path)
            st.image(attached_photo, caption="Photo submitted", width=300)
            st.success(f"Logged as **{record['category']}** ({record['urgency']} urgency) — {record['ward']}")

        elif raw_text.strip():
            with st.spinner("Gemma 4 is structuring your report..."):
                record = gc.classify_complaint(raw_text)
                record["phone"] = phone.strip()
                record["ward"] = ward_choice
                ds.add_complaint(record)
            st.success(f"Logged as **{record['category']}** ({record['urgency']} urgency) — {record['ward']}")

        else:
            st.warning("Type a message, record a voice note, or attach a photo before sending.")

# ---------------------------------------------------------------------------
# PUBLIC PORTAL -- hotspot table + Responsiveness Clock
# ---------------------------------------------------------------------------
with tab_public:
    st.subheader("Community hotspots")
    df = ds.load_complaints()

    if df.empty:
        st.info("No reports yet. Submit one under the 'Submit a Report' tab.")
    else:
        col1, col2, col3 = st.columns(3)
        col1.metric("Total reports", len(df))
        col2.metric("High urgency (open)", int((df["urgency"] == "High").sum()))
        col3.metric("Longest unresolved", f"{int(df['days_unresolved'].max())} days")

        wards = ["All"] + sorted(df["ward"].dropna().unique().tolist())
        categories = ["All"] + sorted(df["category"].dropna().unique().tolist())
        c1, c2 = st.columns(2)
        ward_filter = c1.selectbox("Filter by ward", wards)
        category_filter = c2.selectbox("Filter by category", categories)

        view = df.copy()
        if ward_filter != "All":
            view = view[view["ward"] == ward_filter]
        if category_filter != "All":
            view = view[view["category"] == category_filter]

        dash_col, clock_col = st.columns([1, 1])

        with dash_col:
            st.markdown("#### 📊 Complaint Hotspots by Subcounty")

            area_view = view.copy()
            area_view["subcounty"] = area_view["ward"].map(gc.WARD_TO_SUBCOUNTY).fillna("Other")

            subcounty_view_choice = st.selectbox(
                "Select Subcounty View:",
                ["All Subcounties (Category Breakdown)"] + sorted(gc.SUBCOUNTIES),
                key="top_subcounty_view",
            )

            if subcounty_view_choice == "All Subcounties (Category Breakdown)":
                subcounty_breakdown = pd.crosstab(area_view["subcounty"], area_view["category"])
                st.bar_chart(subcounty_breakdown, stack=False)
            else:
                filtered_subcounty = area_view[area_view["subcounty"] == subcounty_view_choice]
                single_subcounty_breakdown = pd.crosstab(filtered_subcounty["subcounty"], filtered_subcounty["category"])
                st.bar_chart(single_subcounty_breakdown, stack=False)

            st.markdown("###### Narrow down to wards in a subcounty")
            drill_choice = st.selectbox(
                "Select a subcounty to see its ward breakdown:",
                sorted(gc.SUBCOUNTIES),
                key="ward_subcounty_view",
            )

            ward_subset = area_view[area_view["subcounty"] == drill_choice]
            if not ward_subset.empty:
                st.caption(f"Complaint breakdown by wards: {drill_choice} subcounty")
                ward_breakdown = pd.crosstab(ward_subset["ward"], ward_subset["category"])
                st.bar_chart(ward_breakdown, stack=False)
            else:
                st.caption(f"No complaints recorded yet in {drill_choice}.")

        with clock_col:
            st.markdown("#### ⏱️ Responsiveness Clock")
            st.caption("Sorted by urgency, then by how long the issue has gone unaddressed.")

            import urllib.parse
            status_badge = {"Open": "", "Resolved": "✅ **Resolved**", "Disputed": "⚠️ **Disputed by community**"}

            for _, row in view.iterrows():
                urgency_color = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}.get(row["urgency"], "⚪")
                badge = status_badge.get(row["status"], "")

                st.markdown(
                    f"{urgency_color} **{row['category']}** — {row['ward']} {badge}  \n"
                    f"· *{int(row['days_unresolved'])} days unaddressed*  \n"
                    f"> {row['english_summary']}"
                )

                if row["status"] == "Resolved":
                    with st.expander("🚩 This isn't actually fixed"):
                        dispute_reason = st.text_area(
                            "Why do you think this isn't resolved?",
                            key=f"reason_{row['id']}",
                            placeholder="e.g. I passed by yesterday, the pothole is still there.",
                        )
                        if st.button("Submit dispute", key=f"dispute_{row['id']}"):
                            if dispute_reason.strip():
                                ds.dispute_resolution(row["id"], dispute_reason.strip())
                                st.rerun()
                            else:
                                st.warning("Please explain why you're disputing this.")

                if row["status"] in ("Resolved", "Disputed") and row["resolution_note"]:
                    st.caption(f"Resolution claim: {row['resolution_note']} — signed off by {row['resolved_by']} on {row['resolved_date']}")

                share_msg = (
                    f"We have been waiting {int(row['days_unresolved'])} days for action on: "
                    f"{row['category']} issue in {row['ward']} ward. "
                    f"Reported via Sauti-Yetu: {row['english_summary']}"
                )
                wa_link = f"https://wa.me/?text={urllib.parse.quote(share_msg)}"
                st.markdown(f"[📤 Share to WhatsApp]({wa_link})")

                st.divider()

# ---------------------------------------------------------------------------
# ADMIN PORTAL -- gap detector + one-click CDF draft generator
# ---------------------------------------------------------------------------
if tab_admin is not None:
    with tab_admin:
        st.subheader("Administrator tools")
        df = ds.load_complaints()

        if df.empty:
            st.info("No reports yet.")
        else:
            st.markdown("#### Gap detector — clusters by ward & category")
            cluster = (
                df.groupby(["ward", "category"])
                .agg(count=("category", "size"), max_days_unresolved=("days_unresolved", "max"))
                .reset_index()
                .sort_values(by=["count", "max_days_unresolved"], ascending=False)
            )
            st.dataframe(cluster, use_container_width=True, hide_index=True)

            st.markdown("#### One-click CDF Draft Generator")
            wards = sorted(df["ward"].dropna().unique().tolist())
            chosen_ward = st.selectbox("Select ward cluster to draft a proposal for", wards)

            subset = df[df["ward"] == chosen_ward]
            st.write(f"{len(subset)} complaint(s) will be used as evidence for this draft.")

            if st.button("📄 Generate NG-CDF Draft", type="primary"):
                with st.spinner("Gemma 4 is drafting the funding proposal..."):
                    draft = gc.generate_cdf_draft(subset)
                st.text_area("Draft proposal", draft, height=400)
                st.download_button("Download draft (.txt)", draft, file_name=f"CDF_Draft_{chosen_ward}.txt")

            st.markdown("#### Mark a complaint resolved")
            open_complaints = df[df["status"] == "Open"]

            if open_complaints.empty:
                st.info("No open complaints to resolve.")
            else:
                options = {
                    f"{row['category']} — {row['ward']} ({row['english_summary'][:50]}...)": row["id"]
                    for _, row in open_complaints.iterrows()
                }
                chosen_label = st.selectbox("Select complaint to resolve", list(options.keys()))
                chosen_id = options[chosen_label]

                resolution_note = st.text_area(
                    "What was done to resolve it? (required)",
                    placeholder="e.g. County crew filled potholes and regraded the road on 22 July.",
                )
                resolution_photo = st.file_uploader("Attach after-photo (recommended)", type=["jpg", "jpeg", "png"])
                resolved_by = st.text_input("Your name (required — for accountability sign-off)")
                resolved_date = st.date_input("Date resolved")

                if st.button("✅ Mark Resolved", type="primary"):
                    if not resolution_note.strip():
                        st.warning("Please describe what was done before marking this resolved.")
                    elif not resolved_by.strip():
                        st.warning("Please enter your name to sign off on this resolution.")
                    else:
                        photo_path = ""
                        if resolution_photo is not None:
                            photo_path = os.path.join("data", f"resolved_{chosen_id}.jpg")
                            with open(photo_path, "wb") as f:
                                f.write(resolution_photo.getbuffer())
                        resolved_row = ds.mark_resolved(
                            chosen_id, resolution_note.strip(), resolved_by.strip(),
                            photo_path, resolved_date.strftime("%Y-%m-%d"),
                        )
                        sms_sent = sms.send_resolution_alert(
                            resolved_row.get("phone", ""),
                            resolved_row["category"],
                            resolved_row["ward"],
                        )
                        if resolved_row.get("phone"):
                            if sms_sent:
                                st.success(f"Marked resolved by {resolved_by.strip()} on {resolved_row['resolved_date']}. SMS alert sent.")
                            else:
                                st.success(f"Marked resolved by {resolved_by.strip()} on {resolved_row['resolved_date']}. (SMS mocked — check terminal.)")
                        else:
                            st.success(f"Marked resolved by {resolved_by.strip()} on {resolved_row['resolved_date']}. No phone on file, no SMS sent.")
                        st.rerun()