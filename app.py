"""Streamlit review dashboard. Run: streamlit run app.py"""

from __future__ import annotations

import streamlit as st
from dotenv import load_dotenv

from src import db, tracker

load_dotenv()

st.set_page_config(page_title="JobHunt Co-Pilot", layout="wide")

conn = db.connect()
db.init_db(conn)

review_tab, pipeline_tab = st.tabs(["Review", "Pipeline"])

with review_tab:
    st.subheader("Top matches awaiting review")
    rows = db.top_matches(conn, limit=50, only_unapplied=True)

    if not rows:
        st.info("No matches yet. Run `python run.py all` first.")

    for row in rows:
        with st.container(border=True):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"**{row['title']}** @ {row['company']}  —  score: {row['score']:.1f}")
                st.caption(row["reasons"])
                st.markdown(f"[Job posting]({row['url']})")
                if row["cover_letter"]:
                    with st.expander("Draft cover letter"):
                        st.text_area(
                            "Cover letter",
                            value=row["cover_letter"],
                            key=f"draft_{row['id']}",
                            label_visibility="collapsed",
                        )
                else:
                    st.caption("No draft yet — tailoring (Phase 3) isn't built yet.")
            with col2:
                status = row["status"] or "new"
                st.caption(f"status: {status}")
                if st.button("Mark reviewing", key=f"reviewing_{row['id']}"):
                    tracker.set_status(conn, row["id"], "reviewing")
                    st.rerun()
                if st.button("Mark applied", key=f"applied_{row['id']}"):
                    tracker.set_status(conn, row["id"], "applied")
                    st.rerun()
                if st.button("Reject", key=f"rejected_{row['id']}"):
                    tracker.set_status(conn, row["id"], "rejected")
                    st.rerun()

with pipeline_tab:
    st.subheader("Applications by status")
    columns = st.columns(len(tracker.STATUSES))

    for col, status in zip(columns, tracker.STATUSES):
        with col:
            st.markdown(f"**{status}**")
            job_rows = conn.execute(
                """
                SELECT jobs.title, jobs.company, jobs.url
                FROM applications
                JOIN jobs ON jobs.id = applications.job_id
                WHERE applications.status = ?
                ORDER BY applications.updated_at DESC
                """,
                (status,),
            ).fetchall()
            for job_row in job_rows:
                st.caption(f"{job_row['title']} @ {job_row['company']}")
