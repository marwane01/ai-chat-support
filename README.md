# Chatbi – Phase 2 (MVP Bot)

**Status:** Phase 2 complete – Rooms + FAQ + Fallback via FastAPI `/chat`.

## Quickstart
```powershell
docker compose up -d app

# test
Invoke-RestMethod -Uri "http://127.0.0.1:8000/chat" -Method POST `
  -Body '{"message":"rooms under 200 in Paris"}' `
  -ContentType "application/json"
```

---

# Chatbi – Phase 3 (Production Pilot)

**Status:** Phase 3 complete ✅  
- Memory (Redis): remembers city, budget, occupancy across turns  
- Safety & guardrails: PII scrub + Pydantic validation  
- Observability: Prometheus metrics + Grafana dashboards  
- RAG improvements: Qdrant index (5k FAQs) + reranker  

## Quickstart
```powershell
docker compose up -d --build

# test: Rooms (memory + filters)
$hdr = @{ "X-Session-Id" = "test123" }
Invoke-RestMethod -Uri "http://127.0.0.1:8000/chat" -Method POST -Headers $hdr `
  -Body '{"message":"show rooms in Paris under 200 for 2"}' `
  -ContentType "application/json"

# test: FAQ (RAG)
Invoke-RestMethod -Uri "http://127.0.0.1:8000/chat" -Method POST `
  -Body '{"message":"What is check-in time?"}' `
  -ContentType "application/json"

# test: Safety (PII scrub)
Invoke-RestMethod -Uri "http://127.0.0.1:8000/chat" -Method POST `
  -Body '{"message":"repeat a@b.com and 4111 1111 1111 1111"}' `
  -ContentType "application/json"
```

## Observability
- Prometheus: [http://localhost:9090](http://localhost:9090)  
- Grafana: [http://localhost:3000](http://localhost:3000) (admin/admin)  
- Metrics exposed at [http://localhost:8000/metrics](http://localhost:8000/metrics)
