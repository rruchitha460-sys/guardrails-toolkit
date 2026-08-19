"""
Guardrails dashboard.

Two views:
  1. Live traffic - pass/fail rates per check, pulled from the same
     GuardrailLogger the demo app writes to (via /stats + /recent-ish
     data, or directly against Mongo if you point it there).
  2. Eval results - runs evals/run_eval.py fresh and shows
     precision/recall/FP-FN rates per check and per category.

Run: streamlit run dashboard/app.py
"""

import os
import sys

import streamlit as st
import pandas as pd

# allow running `streamlit run dashboard/app.py` from repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from guardrails.logger import GuardrailLogger
from evals.run_eval import run_eval

st.set_page_config(page_title="Guardrails Dashboard", layout="wide")
st.title("Guardrails + Evaluation Dashboard")

logger = GuardrailLogger(mongo_uri=os.environ.get("MONGO_URI"))

tab_live, tab_eval = st.tabs(["Live Traffic", "Eval Results"])

# ---------------------------------------------------------------- live tab
with tab_live:
    st.subheader("Live guardrail activity")
    st.caption(
        "Reads from the same logger the demo app writes to. "
        "Run a few queries through the demo app first if this looks empty."
    )

    stats = logger.stats()

    if stats["total_runs"] == 0:
        st.info("No runs logged yet. Send some requests to the demo app's /chat endpoint first.")
    else:
        col1, col2 = st.columns(2)
        col1.metric("Total runs", stats["total_runs"])
        col2.metric("Overall pass rate", f"{stats['overall_pass_rate']:.1%}")

        st.markdown("**Per-check fail rate**")
        rows = [
            {"check": name, "total": s["total"], "failed": s["failed"], "fail_rate": s["fail_rate"]}
            for name, s in stats["per_check"].items()
        ]
        df = pd.DataFrame(rows).sort_values("fail_rate", ascending=False)
        st.bar_chart(df.set_index("check")["fail_rate"])
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.markdown("**Recent runs**")
        recent = logger.recent(limit=20)
        recent_rows = []
        for r in recent:
            recent_rows.append({
                "timestamp": r["timestamp"],
                "stage": r["stage"],
                "passed": r["passed"],
                "preview": r["input_text_preview"],
                "latency_ms": round(r["total_latency_ms"], 2),
            })
        st.dataframe(pd.DataFrame(recent_rows), use_container_width=True, hide_index=True)

# ---------------------------------------------------------------- eval tab
with tab_eval:
    st.subheader("Eval suite results")
    st.caption("Runs the full test_cases.py suite fresh against the current pipeline each time.")

    if st.button("Run eval suite"):
        with st.spinner("Running..."):
            report = run_eval()
            summary = report.summary()

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Accuracy", f"{summary['accuracy']:.1%}")
        col2.metric("Precision", f"{summary['precision']:.1%}" if summary["precision"] is not None else "n/a")
        col3.metric("Recall", f"{summary['recall']:.1%}" if summary["recall"] is not None else "n/a")
        col4.metric("Avg latency", f"{summary['avg_latency_ms']:.2f}ms")

        st.markdown("**By category**")
        cat_rows = [
            {"category": cat, "correct": s["correct"], "total": s["total"], "accuracy": s["accuracy"]}
            for cat, s in report.by_category().items()
        ]
        st.dataframe(pd.DataFrame(cat_rows), use_container_width=True, hide_index=True)

        failures = report.failures()
        if failures:
            st.markdown(f"**{len(failures)} failure(s)**")
            fail_rows = [
                {
                    "case_id": f.case_id,
                    "outcome": f.outcome_type,
                    "expected_pass": f.expected_pass,
                    "actual_pass": f.actual_pass,
                    "failed_checks": ", ".join(f.actually_failed_checks) or "-",
                }
                for f in failures
            ]
            st.dataframe(pd.DataFrame(fail_rows), use_container_width=True, hide_index=True)
        else:
            st.success("No failures - pipeline matched every expectation.")
    else:
        st.info("Click the button to run the eval suite against the current pipeline.")