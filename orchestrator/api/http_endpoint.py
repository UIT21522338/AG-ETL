# Webhook endpoint — nhận event từ NiFi / Teams / ChatOps
# Framework: FastAPI (pip install fastapi uvicorn)

from fastapi import FastAPI, Request
from orchestrator.router.event_router import route_event

app = FastAPI(title="ETL NiFi Agent Orchestrator")

@app.post("/webhook/nifi")
async def nifi_webhook(request: Request):
    payload = await request.json()
    event_type = payload.get("event_type", "nifi_error")
    agent = route_event(event_type, payload)
    return {"routed_to": agent, "status": "received"}

@app.get("/health")
def health():
    return {"status": "ok"}
