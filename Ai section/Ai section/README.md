# Honeypot OpenAI - Quick Start (Beginner Friendly)

1. Install Docker Desktop and enable Docker Compose
2. Create project folder and paste files exactly as shown (keep structure)

Project structure should be:
```
honeypot-openai/
├─ cognitive/
│  ├─ Dockerfile
│  ├─ app.py
│  └─ requirements.txt
├─ docker-compose.yml
├─ logstash.conf
└─ .env
```

3. Copy `.env.example` to `.env` and put your OpenAI API key.
4. Run:
```
docker compose up --build
```
5. Test cognitive endpoint:
```
curl -X POST http://localhost:5000/act -H "Content-Type: application/json" -d '{
  "session_id":"sess-1",
  "src_ip":"5.6.7.8",
  "input":"cat /etc/passwd",
  "history":[]
}'
```
6. Open Kibana at `http://localhost:5601` and look for index `honeypot-*` to view logs.

Notes:
- Keep your API key private.
- Use a cheap model or limit requests to reduce cost during development.
- Do not attach this to a production network without isolation.
