# UMKM AI Assistant

This project is a prototype AI assistant for the operational needs of SMEs (Small and Medium Enterprises). The application combines a `FastAPI` backend, agent orchestration with `LangGraph`, Google Gemini model through `LangChain`, and a simple Streamlit-based chat interface.

## Key Features

- Chat assistant to support SME operational needs
- Agent workflow based on `LangGraph`
- Tool integration for:
  - Inventory stock checks
  - Schedule management
- Backend API with `FastAPI`
- Simple chat UI with `Streamlit`
- Containerization support using `Docker`

## Project Structure

```text
.
|-- app.py             # Streamlit Frontend
|-- main.py            # FastAPI Backend + LangGraph Agent
|-- tools.py           # Agent Tools: inventory check & calendar scheduling
|-- requirements.txt   # Python dependency list
|-- Dockerfile         # Backend container configuration
|-- run_ui.sh          # Script to run Streamlit UI
|-- cek_model.py       # Utility to check available Gemini models
`-- test_ai.py         # Utility to test Vertex AI model access across regions
```

## How It Works (Brief Overview)

1. User sends a question via the UI or directly to the API endpoint.
2. Backend receives request at `/api/v1/assist` endpoint.
3. `LangGraph` agent processes the message using the Gemini model.
4. If needed, the agent calls tools from `tools.py`.
5. Final result is returned as a text response.

## Tech Stack

- Python 3.10+
- FastAPI
- Uvicorn
- Streamlit
- LangChain
- LangGraph
- Google Vertex AI (Gemini models)
- Docker

## Installation

Clone the repository and install backend dependencies:

```bash
pip install -r requirements.txt
```

To run the Streamlit UI, also install additional dependencies:

```bash
pip install streamlit requests
```

## Environment Variables

This project requires Google Vertex AI credentials:

```bash
GOOGLE_CLOUD_PROJECT=your_project_id
VERTEX_PROJECT_ID=your_project_id
GOOGLE_API_KEY=your_google_api_key
```

On Windows PowerShell:

```powershell
$env:GOOGLE_CLOUD_PROJECT="your_project_id"
$env:GOOGLE_API_KEY="your_google_api_key"
```

## Running Backend Locally

```bash
uvicorn main:app --reload
```

By default, the backend will be available at:

```text
http://127.0.0.1:8000
```

Example endpoint:

```text
POST /api/v1/assist
```

Example request body:

```json
{
  "query": "Please check the arabica coffee bean stock",
  "session_id": "optional-session-id"
}
```

## Running Streamlit UI

```bash
streamlit run app.py
```

Or use the provided script:

```bash
sh run_ui.sh
```

## Important Notes

- The `app.py` file currently uses `API_URL` pointing to the Cloud Run backend, not localhost.
- To connect the UI to a local backend, change the `API_BASE_URL` in `app.py` to point to your local endpoint:

```python
API_BASE_URL = "http://127.0.0.1:8000"
```

## Running with Docker

Build the image:

```bash
docker build -t umkm-agent .
```

Run the container:

```bash
docker run -p 8080:8080 \
  -e GOOGLE_CLOUD_PROJECT=your_project_id \
  -e GOOGLE_API_KEY=your_google_api_key \
  umkm-agent
```

The backend will run at:

```text
http://127.0.0.1:8080
```

## Available Tools

### 1. Check Inventory Stock

The `cek_stok_barang` tool checks UMKM inventory levels based on item name.

Example items available in the simulation:

- arabica coffee beans (biji kopi arabika)
- palm sugar (gula aren)
- fresh milk (susu fresh)
- 16 oz cups (cup 16 oz)

### 2. Create Calendar Schedule

The `buat_jadwal_kalender` tool creates activity schedules or meeting schedules in a simulated manner.

## Additional Utilities

- `cek_model.py`: Helps check which Gemini models are available for your `GOOGLE_API_KEY`
- `test_ai.py`: Helps test which Vertex AI regions are accessible to your project

Note:

- Both utility files above may require additional dependencies not yet listed in `requirements.txt`.

## Project Status

This project is still a prototype/demo and some integrations still use simulated data, particularly for inventory and calendar features.

## Future Development Suggestions

- Connect inventory tool to a real database
- Integrate with actual Google Calendar API
- Add authentication to the API
- Add logging and monitoring
- Separate environment configuration into `.env` file
- Add multi-language support
- Implement persistent session management with database
- Add more specialized agents (Finance, HR, Marketing)

## License

To be determined. Add an appropriate license before publishing this repository more widely.
