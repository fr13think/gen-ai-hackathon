from __future__ import annotations

import base64
import os
from uuid import uuid4

import requests
import streamlit as st


API_BASE_URL = os.getenv("UMKM_API_BASE_URL", "https://umkm-agent-api-382375274988.us-central1.run.app")
ASSIST_URL = f"{API_BASE_URL}/api/v1/assist"
DASHBOARD_URL = f"{API_BASE_URL}/api/v1/dashboard"
ANALYZE_INVOICE_URL = f"{API_BASE_URL}/api/v1/analyze-invoice"


st.set_page_config(page_title="UMKM AI Copilot", page_icon="🏪", layout="wide")

st.markdown(
    """
    <style>
    .stApp {
        background:
            radial-gradient(circle at top left, rgba(227, 175, 84, 0.22), transparent 28%),
            linear-gradient(180deg, #f7f3ea 0%, #fffdf7 55%, #f4efe4 100%);
    }
    .hero-card {
        padding: 1.25rem 1.5rem;
        border-radius: 20px;
        background: linear-gradient(135deg, #17322f 0%, #29524d 100%);
        color: #f7f0df;
        box-shadow: 0 12px 32px rgba(23, 50, 47, 0.18);
        margin-bottom: 1rem;
    }
    .soft-card {
        padding: 1rem 1.1rem;
        border-radius: 18px;
        background: rgba(255, 251, 242, 0.9);
        border: 1px solid rgba(41, 82, 77, 0.08);
        box-shadow: 0 10px 24px rgba(56, 49, 36, 0.06);
    }
    .mini-label {
        font-size: 0.82rem;
        color: #5e5a4c;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }
    .metric-big {
        font-size: 1.8rem;
        font-weight: 700;
        color: #17322f;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def format_rupiah(amount: int) -> str:
    return f"Rp{amount:,.0f}".replace(",", ".")


def render_list_card(items: list[str], extra_style: str = "") -> None:
    list_html = "".join(f"<li>{item}</li>" for item in items)
    st.markdown(
        f"""
        <div class="soft-card" style="{extra_style}">
            <ul style="margin:0; padding-left:1.2rem;">
                {list_html}
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )


def fetch_dashboard() -> dict:
    response = requests.get(DASHBOARD_URL, timeout=20)
    response.raise_for_status()
    return response.json()["data"]


def analyze_invoice(uploaded_file) -> dict:
    file_bytes = uploaded_file.getvalue()
    response = requests.post(
        ANALYZE_INVOICE_URL,
        json={
            "filename": uploaded_file.name,
            "mime_type": uploaded_file.type or "image/jpeg",
            "file_data_base64": base64.b64encode(file_bytes).decode("utf-8"),
        },
        headers={"Content-Type": "application/json"},
        timeout=90,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("status") != "success":
        raise RuntimeError(payload.get("message", "Unknown analysis error"))
    return payload["data"]


def ask_assistant(prompt: str, session_id: str) -> dict:
    response = requests.post(
        ASSIST_URL,
        json={"query": prompt, "session_id": session_id},
        headers={"Content-Type": "application/json"},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "Hello, I am ready to help as your AI Operations Copilot. "
                "I can summarize business performance, check critical inventory, and recommend priority actions."
            ),
            "agents": ["operations"],
        }
    ]
if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None
if "invoice_analysis" not in st.session_state:
    st.session_state.invoice_analysis = None

try:
    dashboard = fetch_dashboard()
except Exception as exc:
    dashboard = None
    st.error(f"Failed to load the dashboard from the backend: {exc}")

st.markdown(
    """
    <div class="hero-card">
        <div style="font-size:0.9rem; letter-spacing:0.08em; text-transform:uppercase;">UMKM AI Copilot</div>
        <div style="font-size:2.1rem; font-weight:700; margin-top:0.35rem;">From a simple chatbot to an operational control desk.</div>
        <div style="margin-top:0.55rem; max-width:780px;">
            Monitor daily performance, detect critical inventory, request recommended actions, and delegate analysis to the copilot.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

if dashboard:
    profile = dashboard["profile"]
    metrics = dashboard["metrics"]

    top_cols = st.columns([1.1, 1.1, 1.1, 1.2])
    top_cols[0].markdown(
        f"""
        <div class="soft-card">
            <div class="mini-label">Today's Revenue</div>
            <div class="metric-big">{format_rupiah(metrics['omzet_hari_ini'])}</div>
            <div>{profile['nama']} • {profile['kota']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    top_cols[1].markdown(
        f"""
        <div class="soft-card">
            <div class="mini-label">Estimated Transactions</div>
            <div class="metric-big">{metrics['total_transaksi_estimasi']}</div>
            <div>Operating hours {profile['jam_operasional']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    top_cols[2].markdown(
        f"""
        <div class="soft-card">
            <div class="mini-label">Top Product</div>
            <div class="metric-big" style="font-size:1.35rem;">{metrics['produk_terlaris']}</div>
            <div>Today's sales performance</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    top_cols[3].markdown(
        f"""
        <div class="soft-card">
            <div class="mini-label">Critical Inventory</div>
            <div class="metric-big">{metrics['stok_kritis_count']}</div>
            <div>Needs immediate attention</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    left_col, right_col = st.columns([1.35, 1])

    with left_col:
        st.subheader("Operational Summary")
        render_list_card(dashboard["rekomendasi_hari_ini"])

        st.subheader("Product Performance")
        sales_cols = st.columns(len(dashboard["penjualan"]))
        for col, sale in zip(sales_cols, dashboard["penjualan"]):
            col.markdown(
                f"""
                <div class="soft-card">
                    <div class="mini-label">{sale['produk']}</div>
                    <div class="metric-big" style="font-size:1.25rem;">{sale['terjual_hari_ini']}</div>
                    <div>{format_rupiah(sale['pendapatan'])}</div>
                    <div>Margin {int(sale['margin'] * 100)}%</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with right_col:
        st.subheader("Critical Inventory")
        for item in dashboard["stok_kritis"]:
            st.markdown(
                f"""
                <div class="soft-card" style="margin-bottom:0.7rem;">
                    <div class="mini-label">{item['nama']}</div>
                    <div class="metric-big" style="font-size:1.2rem;">{item['stok']}</div>
                    <div>Supplier: {item['supplier']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.subheader("Quick Actions")
        for index, action in enumerate(dashboard["quick_actions"]):
            if st.button(action, key=f"quick_action_{index}", use_container_width=True):
                st.session_state.pending_prompt = action

st.subheader("Invoice / Photo Insights")
upload_col, result_col = st.columns([0.95, 1.4])

with upload_col:
    st.markdown(
        """
        <div class="soft-card">
            <div class="mini-label">Upload Document</div>
            <div style="margin-top:0.35rem;">Upload an invoice, receipt, or supplier purchase photo to extract key fields and business insights.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    uploaded_file = st.file_uploader(
        "Choose an invoice or photo",
        type=["png", "jpg", "jpeg", "webp"],
        accept_multiple_files=False,
    )
    if uploaded_file is not None:
        st.image(uploaded_file, caption=uploaded_file.name, use_container_width=True)
        if st.button("Analyze Document", use_container_width=True):
            with st.spinner("Extracting fields and business insights from the document..."):
                try:
                    st.session_state.invoice_analysis = analyze_invoice(uploaded_file)
                except Exception as exc:
                    st.session_state.invoice_analysis = {"error": str(exc)}

with result_col:
    st.markdown(
        """
        <div class="soft-card">
            <div class="mini-label">Analysis Result</div>
            <div style="margin-top:0.35rem;">The copilot will extract supplier, total spend, line items, risks, and next-step recommendations.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    analysis = st.session_state.invoice_analysis
    if analysis:
        if analysis.get("error"):
            st.error(f"Document analysis failed: {analysis['error']}")
        else:
            info_cols = st.columns(4)
            info_cols[0].metric("Document Type", analysis.get("document_type") or "-")
            info_cols[1].metric("Supplier", analysis.get("supplier_name") or "-")
            info_cols[2].metric("Invoice Date", analysis.get("invoice_date") or "-")
            info_cols[3].metric("Total Amount", analysis.get("total_amount") or "-")

            st.markdown("**Summary**")
            st.markdown(
                f"""
                <div class="soft-card" style="margin-bottom:0.8rem;">
                    {analysis.get('summary') or 'No summary returned.'}
                </div>
                """,
                unsafe_allow_html=True,
            )

            meta_cols = st.columns(2)
            meta_cols[0].markdown(f"**Invoice Number:** {analysis.get('invoice_number') or '-'}")
            meta_cols[1].markdown(f"**Payment Status:** {analysis.get('payment_status') or '-'}")

            if analysis.get("line_items"):
                st.markdown("**Line Items**")
                st.dataframe(analysis["line_items"], use_container_width=True)

            detail_cols = st.columns(3)
            with detail_cols[0]:
                st.markdown("**Insights**")
                render_list_card(analysis.get("insights") or ["No insight extracted."])
            with detail_cols[1]:
                st.markdown("**Risks**")
                render_list_card(analysis.get("risks") or ["No immediate risk detected."])
            with detail_cols[2]:
                st.markdown("**Recommended Actions**")
                render_list_card(analysis.get("recommended_actions") or ["No action recommended."])
    else:
        st.info("No document analyzed yet. Upload an invoice or supplier photo to see extracted insights here.")

st.subheader("Copilot Chat")
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("agents"):
            st.caption("Agents used: " + ", ".join(agent.title() for agent in msg["agents"]))

prompt = st.chat_input("Ask the copilot or use one of the quick actions above...")
if st.session_state.pending_prompt and not prompt:
    prompt = st.session_state.pending_prompt
    st.session_state.pending_prompt = None

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("The copilot is analyzing your business operations..."):
            try:
                payload = ask_assistant(prompt, st.session_state.session_id)
                answer = payload["response"]
                st.session_state.session_id = payload["session_id"]
                st.markdown(answer)
                if payload.get("agents"):
                    st.caption("Agents used: " + ", ".join(agent.title() for agent in payload["agents"]))
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": answer,
                        "agents": payload.get("agents", []),
                    }
                )
            except Exception as exc:
                error_message = f"Failed to connect to the backend: {exc}"
                st.error(error_message)
                st.session_state.messages.append({"role": "assistant", "content": error_message})
