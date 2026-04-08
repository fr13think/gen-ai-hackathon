import os
from fastapi import FastAPI
from pydantic import BaseModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage, HumanMessage
import operator

# Import ToolNode untuk mengeksekusi alat secara otomatis
from langgraph.prebuilt import ToolNode 

from tools import cek_stok_barang, buat_jadwal_kalender

app = FastAPI(title="API UMKM Agent")

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,
    google_api_key=os.environ.get("GOOGLE_API_KEY")
)

tools = [cek_stok_barang, buat_jadwal_kalender]
llm_with_tools = llm.bind_tools(tools)

# Node 1: Supervisor (Berpikir)
def supervisor_node(state: AgentState):
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}

# Node 2: Eksekutor Tools
tool_node = ToolNode(tools)

# Logika Rute: Apakah LLM memanggil tool atau sudah selesai?
def should_continue(state: AgentState):
    messages = state['messages']
    last_message = messages[-1]
    # Jika LLM memutuskan memanggil tool, arahkan ke node 'tools'
    if last_message.tool_calls:
        return "tools"
    # Jika tidak ada pemanggilan tool, berarti sudah selesai
    return END

# Bangun Graf (Looping)
workflow = StateGraph(AgentState)
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("tools", tool_node)

workflow.set_entry_point("supervisor")

# Tambahkan Edge/Jalur
workflow.add_conditional_edges("supervisor", should_continue)
workflow.add_edge("tools", "supervisor") # Setelah tool dieksekusi, KEMBALI ke supervisor

app_graph = workflow.compile()

class QueryRequest(BaseModel):
    query: str

@app.post("/api/v1/assist")
async def assist(request: QueryRequest):
    result = app_graph.invoke({"messages": [HumanMessage(content=request.query)]})
    final_message = result["messages"][-1]
    
    # LOGIKA PEMBERSIHAN (Cleaning):
    # Jika jawaban berupa list (seperti yang Anda alami), ambil teksnya saja
    raw_content = final_message.content
    if isinstance(raw_content, list):
        # Mengambil elemen yang bertipe 'text'
        clean_text = " ".join([item['text'] for item in raw_content if 'text' in item])
    else:
        clean_text = raw_content

    return {
        "status": "success", 
        "response": clean_text
    }