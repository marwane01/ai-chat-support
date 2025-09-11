@'
# Chatbi – Phase 2 (MVP Bot)

**Status:** Phase 2 complete – Rooms + FAQ + Fallback via FastAPI `/chat`.

## Quickstart
```bash
docker compose up -d app
# test
curl -s -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\":\"rooms under 200 in Paris\"}"