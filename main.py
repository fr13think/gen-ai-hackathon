import base64
import json
import operator
import os
import re
from typing import Annotated, Any, Sequence, TypedDict
from uuid import uuid4

from fastapi import FastAPI
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_google_vertexai import ChatVertexAI
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel

from tools import (
    BUSINESS_PROFILE,
    analisis_produk_terlaris,
    buat_jadwal_kalender,
    cek_stok_barang,
    get_dashboard_snapshot,
    rekomendasi_restock_hari_ini,
    ringkasan_operasional_hari_ini,
)

app = FastAPI(title="API UMKM Agent")


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]


class QueryRequest(BaseModel):
    query: str
    session_id: str | None = None


class InvoiceAnalysisRequest(BaseModel):
    filename: str
    mime_type: str
    file_data_base64: str


SYSTEM_PROMPT = f"""
You are the AI Operations Copilot for an SME called {BUSINESS_PROFILE['nama']} in {BUSINESS_PROFILE['kota']}.
Your job is to help the owner make operational decisions, not just answer like a generic chatbot.

Working rules:
- Use tools whenever the request involves inventory, sales performance, restock recommendations, or scheduling.
- Keep answers concise, sharp, and action-oriented.
- If there is business risk, mention the highest priority first.
- When relevant, end with a 'Recommended Actions' section with 2-3 concrete next steps.
- Never claim that a real external integration was executed if the tool result is still simulated.
""".strip()

VERTEX_PROJECT = os.getenv("VERTEX_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT") or "gen-ai-hackathon-492712"
VERTEX_LOCATION = os.getenv("VERTEX_LOCATION", "us-central1")
VERTEX_CHAT_MODEL = os.getenv("VERTEX_CHAT_MODEL", os.getenv("VERTEX_MODEL", "gemini-1.5-flash-001"))
VERTEX_VISION_MODEL = os.getenv("VERTEX_VISION_MODEL", "gemini-2.5-flash-image")

llm = ChatVertexAI(
    model_name=VERTEX_CHAT_MODEL,
    project=VERTEX_PROJECT,
    location=VERTEX_LOCATION,
    temperature=0.2,
    max_retries=1,
)

vision_llm = ChatVertexAI(
    model_name=VERTEX_VISION_MODEL,
    project=VERTEX_PROJECT,
    location=VERTEX_LOCATION,
    temperature=0,
    max_retries=1,
)

AGENT_PROMPTS = {
    "inventory": """
You are the Inventory Agent.
Focus on stock levels, reorder urgency, supplier readiness, and inventory risk.
Always prioritize operational safety and mention if any item may affect sales continuity.
""".strip(),
    "sales": """
You are the Sales Agent.
Focus on product performance, revenue signals, margin opportunities, and promotion ideas.
Recommend practical actions that can improve revenue or product mix in the next business cycle.
""".strip(),
    "operations": """
You are the Operations Agent.
Focus on daily execution, scheduling, owner priorities, and short action plans.
Keep the response practical and easy to execute by a small business owner.
""".strip(),
    "synthesis": """
You are the Supervisor Agent.
Combine specialist findings into one concise response with these sections:
Summary
Key Risks
Recommended Actions
Keep it sharp, non-repetitive, and business-oriented.
""".strip(),
}

tools = [
    cek_stok_barang,
    rekomendasi_restock_hari_ini,
    ringkasan_operasional_hari_ini,
    analisis_produk_terlaris,
    buat_jadwal_kalender,
]
llm_with_tools = llm.bind_tools(tools)
tool_node = ToolNode(tools)
session_store: dict[str, list[BaseMessage]] = {}


def should_continue(state: AgentState):
    last_message = state["messages"][-1]
    if getattr(last_message, "tool_calls", None):
        return "tools"
    return END


def _build_specialist_app(system_prompt: str, specialist_tools: list):
    specialist_llm = llm.bind_tools(specialist_tools)
    specialist_tool_node = ToolNode(specialist_tools)

    def specialist_node(state: AgentState):
        response = specialist_llm.invoke([SystemMessage(content=system_prompt), *state["messages"]])
        return {"messages": [response]}

    specialist_workflow = StateGraph(AgentState)
    specialist_workflow.add_node("specialist", specialist_node)
    specialist_workflow.add_node("tools", specialist_tool_node)
    specialist_workflow.set_entry_point("specialist")
    specialist_workflow.add_conditional_edges("specialist", should_continue)
    specialist_workflow.add_edge("tools", "specialist")
    return specialist_workflow.compile()


inventory_app = _build_specialist_app(
    AGENT_PROMPTS["inventory"],
    [cek_stok_barang, rekomendasi_restock_hari_ini],
)
sales_app = _build_specialist_app(
    AGENT_PROMPTS["sales"],
    [analisis_produk_terlaris],
)
operations_app = _build_specialist_app(
    AGENT_PROMPTS["operations"],
    [ringkasan_operasional_hari_ini, buat_jadwal_kalender],
)


def supervisor_node(state: AgentState):
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}


workflow = StateGraph(AgentState)
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("tools", tool_node)
workflow.set_entry_point("supervisor")
workflow.add_conditional_edges("supervisor", should_continue)
workflow.add_edge("tools", "supervisor")
app_graph = workflow.compile()


def _clean_message_content(message: BaseMessage) -> str:
    raw_content = message.content
    if isinstance(raw_content, list):
        return " ".join(item["text"] for item in raw_content if isinstance(item, dict) and "text" in item)
    return str(raw_content)


def _route_agents(query: str) -> list[str]:
    lowered = query.lower()
    agents: list[str] = []

    inventory_keywords = ["stock", "inventory", "restock", "supplier", "stok", "reorder"]
    sales_keywords = ["sales", "revenue", "promo", "margin", "product", "terlaris", "omzet"]
    operations_keywords = ["schedule", "calendar", "meeting", "plan", "prioritize", "today", "operational", "briefing", "jadwal"]

    if any(keyword in lowered for keyword in inventory_keywords):
        agents.append("inventory")
    if any(keyword in lowered for keyword in sales_keywords):
        agents.append("sales")
    if any(keyword in lowered for keyword in operations_keywords):
        agents.append("operations")

    broad_strategy_signals = [
        "what should i prioritize",
        "what should i do",
        "plan for today",
        "plan for tomorrow",
        "overall",
        "business health",
        "full summary",
        "recommended actions",
    ]
    if any(signal in lowered for signal in broad_strategy_signals):
        return ["inventory", "sales", "operations"]

    return agents or ["operations"]


def _run_specialist_agent(agent_name: str, history: list[BaseMessage], query: str) -> str:
    specialist_apps = {
        "inventory": inventory_app,
        "sales": sales_app,
        "operations": operations_app,
    }
    result = specialist_apps[agent_name].invoke({"messages": [*history, HumanMessage(content=query)]})
    return _clean_message_content(result["messages"][-1])


def _local_specialist_reply(agent_name: str, query: str) -> str:
    lowered = query.lower()
    if agent_name == "inventory":
        if any(keyword in lowered for keyword in ["stock", "inventory", "stok"]):
            snapshot = get_dashboard_snapshot()
            inventory_names = [item["nama"] for item in snapshot["stok_kritis"]] + ["gula aren", "cup 16 oz"]
            for item_name in inventory_names:
                if item_name in lowered:
                    return cek_stok_barang.invoke({"nama_barang": item_name})
        return rekomendasi_restock_hari_ini.invoke({})

    if agent_name == "sales":
        return analisis_produk_terlaris.invoke({})

    if any(keyword in lowered for keyword in ["schedule", "meeting", "calendar", "jadwal", "kalender"]):
        kegiatan, waktu = _extract_schedule_request(query)
        return buat_jadwal_kalender.invoke({"kegiatan": kegiatan, "waktu": waktu})
    return ringkasan_operasional_hari_ini.invoke({})


def _synthesize_multi_agent_response(query: str, specialist_outputs: dict[str, str]) -> str:
    synthesis_input = "\n\n".join(
        f"{agent_name.title()} Agent Findings:\n{agent_output}"
        for agent_name, agent_output in specialist_outputs.items()
    )
    response = llm.invoke(
        [
            SystemMessage(content=AGENT_PROMPTS["synthesis"]),
            HumanMessage(content=f"User request: {query}\n\n{synthesis_input}"),
        ]
    )
    return _clean_message_content(response)


def _local_synthesis_response(specialist_outputs: dict[str, str]) -> str:
    sections = ["Summary"]
    if "operations" in specialist_outputs:
        sections.append(specialist_outputs["operations"])
    else:
        sections.append(next(iter(specialist_outputs.values())))

    risk_parts = []
    if "inventory" in specialist_outputs:
        risk_parts.append(specialist_outputs["inventory"])
    if "sales" in specialist_outputs:
        risk_parts.append(specialist_outputs["sales"])

    response = "\n\n".join(
        [
            "Summary\n" + sections[1],
            "Key Risks\n" + ("\n".join(f"- {part}" for part in risk_parts) if risk_parts else "- No major risk detected."),
            "Recommended Actions\n" + "\n".join(
                f"- Review the {agent_name} recommendation and execute the highest-priority item first."
                for agent_name in specialist_outputs.keys()
            ),
        ]
    )
    return response


def _extract_json_object(raw_text: str) -> dict[str, Any]:
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def _safe_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    return []


def _safe_line_items(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    sanitized: list[dict[str, Any]] = []
    for item in value:
        if isinstance(item, dict):
            sanitized.append(
                {
                    "name": str(item.get("name", "")).strip(),
                    "quantity": str(item.get("quantity", "")).strip(),
                    "unit_price": str(item.get("unit_price", "")).strip(),
                    "line_total": str(item.get("line_total", "")).strip(),
                }
            )
    return sanitized


def _analyze_invoice_document(filename: str, mime_type: str, file_data_base64: str) -> dict[str, Any]:
    prompt = """
You are an expert finance and operations assistant for small businesses.
Analyze this invoice, receipt, or supplier purchase photo and return valid JSON only.

Return exactly this schema:
{
  "document_type": "invoice|receipt|purchase_note|unknown",
  "supplier_name": "",
  "invoice_number": "",
  "invoice_date": "",
  "currency": "",
  "total_amount": "",
  "payment_status": "",
  "line_items": [
    {
      "name": "",
      "quantity": "",
      "unit_price": "",
      "line_total": ""
    }
  ],
  "summary": "",
  "insights": [],
  "risks": [],
  "recommended_actions": []
}

Instructions:
- If a field is missing, use an empty string.
- Keep summary to 2 sentences max.
- Keep insights, risks, and recommended_actions concise and business-oriented.
- Focus on supplier, spend, unusual items, restocking relevance, and follow-up urgency.
""".strip()

    message = HumanMessage(
        content=[
            {"type": "text", "text": prompt},
            {
                "type": "image_url",
                "image_url": {"url": f"data:{mime_type};base64,{file_data_base64}"},
            },
        ]
    )
    response = vision_llm.invoke([message])
    parsed = _extract_json_object(_clean_message_content(response))
    return {
        "filename": filename,
        "document_type": str(parsed.get("document_type", "unknown")),
        "supplier_name": str(parsed.get("supplier_name", "")),
        "invoice_number": str(parsed.get("invoice_number", "")),
        "invoice_date": str(parsed.get("invoice_date", "")),
        "currency": str(parsed.get("currency", "")),
        "total_amount": str(parsed.get("total_amount", "")),
        "payment_status": str(parsed.get("payment_status", "")),
        "summary": str(parsed.get("summary", "")),
        "insights": _safe_list(parsed.get("insights")),
        "risks": _safe_list(parsed.get("risks")),
        "recommended_actions": _safe_list(parsed.get("recommended_actions")),
        "line_items": _safe_line_items(parsed.get("line_items")),
    }


def _extract_schedule_request(query: str) -> tuple[str, str]:
    lowered = query.lower()
    waktu = "tomorrow at 09.00 WIB"

    for candidate in [
        "tomorrow morning",
        "tomorrow afternoon",
        "tomorrow evening",
        "tomorrow at 09.00",
        "tomorrow at 10.00",
        "tomorrow at 14.00",
        "today at 15.00",
        "today at 16.00",
        "besok pagi",
        "besok siang",
        "besok sore",
        "besok jam 09.00",
        "besok jam 10.00",
        "besok jam 14.00",
        "hari ini jam 15.00",
        "hari ini jam 16.00",
    ]:
        if candidate in lowered:
            waktu = (
                candidate.replace("jam", "pukul")
                .replace("tomorrow", "tomorrow")
                .replace("today", "today")
            )
            break

    match = re.search(r"(tomorrow|today|besok|hari ini)\s+(?:jam|at)\s+(\d{1,2}(?:[:.]\d{2})?)", lowered)
    if match:
        jam = match.group(2).replace(":", ".")
        day_map = {
            "tomorrow": "tomorrow",
            "today": "today",
            "besok": "tomorrow",
            "hari ini": "today",
        }
        waktu = f"{day_map.get(match.group(1), match.group(1))} at {jam} WIB"

    kegiatan = query.strip()
    prefixes = [
        "schedule",
        "schedule a",
        "schedule an",
        "set up",
        "set up a",
        "set up an",
        "create a schedule for",
        "jadwalkan",
        "buat jadwal",
        "atur jadwal",
        "tolong jadwalkan",
    ]
    for prefix in prefixes:
        if lowered.startswith(prefix):
            kegiatan = query[len(prefix) :].strip(" :,-")
            break

    time_phrases = [
        "for tomorrow morning",
        "for tomorrow afternoon",
        "for tomorrow evening",
        "for today afternoon",
        "for today evening",
        "tomorrow morning",
        "tomorrow afternoon",
        "tomorrow evening",
        "today afternoon",
        "today evening",
        "besok pagi",
        "besok siang",
        "besok sore",
    ]
    lowered_activity = kegiatan.lower()
    for phrase in time_phrases:
        if lowered_activity.endswith(phrase):
            kegiatan = kegiatan[: -len(phrase)].strip(" ,.-")
            break

    if not kegiatan:
        kegiatan = "operations meeting"

    return kegiatan, waktu


def _local_copilot_reply(query: str) -> str:
    lowered = query.lower()
    snapshot = get_dashboard_snapshot()

    inventory_names = [item["nama"] for item in snapshot["stok_kritis"]]
    known_items = inventory_names + ["gula aren", "cup 16 oz"]

    if any(keyword in lowered for keyword in ["ringkasan", "summary", "operasional", "briefing"]):
        return ringkasan_operasional_hari_ini.invoke({})

    if any(keyword in lowered for keyword in ["restock", "stok kritis", "stok menipis", "reorder", "critical stock", "critical inventory"]):
        return rekomendasi_restock_hari_ini.invoke({})

    if any(keyword in lowered for keyword in ["terlaris", "promo", "margin", "produk terbaik", "best-selling", "highest-margin", "top product"]):
        return analisis_produk_terlaris.invoke({})

    if any(keyword in lowered for keyword in ["jadwal", "schedule", "meeting", "kalender", "calendar"]):
        kegiatan, waktu = _extract_schedule_request(query)
        return buat_jadwal_kalender.invoke({"kegiatan": kegiatan, "waktu": waktu})

    if "stok" in lowered or "stock" in lowered or "inventory" in lowered:
        for item_name in known_items:
            if item_name in lowered:
                return cek_stok_barang.invoke({"nama_barang": item_name})
        return (
            "I can check inventory for a specific item. Try a request like "
            "'check stock for biji kopi arabika' or 'check stock for susu fresh'."
        )

    metrics = snapshot["metrics"]
    rekomendasi = "\n- ".join(snapshot["rekomendasi_hari_ini"])
    return (
        f"Quick snapshot: today's revenue is {metrics['omzet_hari_ini']:,} rupiah, the top product is "
        f"{metrics['produk_terlaris']}, and there are {metrics['stok_kritis_count']} critical inventory items.\n\n"
        f"Recommended Actions:\n- {rekomendasi}"
    )


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/v1/dashboard")
async def dashboard():
    return {"status": "success", "data": get_dashboard_snapshot()}


@app.post("/api/v1/analyze-invoice")
async def analyze_invoice(request: InvoiceAnalysisRequest):
    try:
        base64.b64decode(request.file_data_base64, validate=True)
    except Exception as exc:
        return {
            "status": "error",
            "message": f"Invalid file payload: {exc}",
        }

    try:
        analysis = _analyze_invoice_document(
            filename=request.filename,
            mime_type=request.mime_type,
            file_data_base64=request.file_data_base64,
        )
        return {
            "status": "success",
            "data": analysis,
        }
    except Exception as exc:
        error_text = str(exc)
        if "Publisher Model" in error_text or "not found" in error_text.lower():
            friendly_message = (
                f"Document analysis failed because the configured vision model '{VERTEX_VISION_MODEL}' "
                "is not available in this Vertex AI project or region. Try another vision-capable model "
                "or verify model access in Vertex AI."
            )
        else:
            friendly_message = f"Document analysis failed: {exc}"
        return {
            "status": "error",
            "message": friendly_message,
        }


@app.post("/api/v1/assist")
async def assist(request: QueryRequest):
    session_id = request.session_id or str(uuid4())
    history = session_store.get(session_id, [])
    agents_used = _route_agents(request.query)
    response_mode = "multi_agent"

    try:
        if len(agents_used) == 1:
            clean_text = _run_specialist_agent(agents_used[0], history, request.query)
        else:
            specialist_outputs = {
                agent_name: _run_specialist_agent(agent_name, history, request.query)
                for agent_name in agents_used
            }
            clean_text = _synthesize_multi_agent_response(request.query, specialist_outputs)
    except Exception as exc:
        if len(agents_used) == 1:
            clean_text = _local_specialist_reply(agents_used[0], request.query)
        else:
            specialist_outputs = {
                agent_name: _local_specialist_reply(agent_name, request.query)
                for agent_name in agents_used
            }
            clean_text = _local_synthesis_response(specialist_outputs)
        error_text = str(exc)
        if "RESOURCE_EXHAUSTED" in error_text or "quota" in error_text.lower():
            note = "System note: this answer used local demo mode because the model quota is currently unavailable."
        elif "503" in error_text or "UNAVAILABLE" in error_text:
            note = "System note: this answer used local demo mode because the model service is temporarily busy."
        else:
            note = "System note: this answer used local demo mode because the model service is temporarily unavailable."
        clean_text += f"\n\n{note}"
        response_mode = "local_fallback"

    updated_history = [*history, HumanMessage(content=request.query), AIMessage(content=clean_text)]
    session_store[session_id] = updated_history[-12:]

    return {
        "status": "success",
        "session_id": session_id,
        "mode": response_mode,
        "agents": agents_used,
        "response": clean_text,
    }
