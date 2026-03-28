🚨 AI Women Safety App — Architecture (Key Points)
📱 Client (Flutter)
🎤 Audio capture (continuous monitoring)
🧠 On-device ML model (distress detection)
🚨 SOS button + cancel option
💬 Chat interface
📍 Real-time GPS tracking
⚙️ Backend (FastAPI)
🚨 /v1/alerts → Receive SOS alerts
💬 /v1/chat → NLP processing
🧾 /v1/summary → LLM summary generation
📢 Notification service (family / police)
📍 Live tracking service
🗄️ Database
🧩 MongoDB → alerts, logs, chats
⚡ Cache (Redis) → live location, sessions
🌍 Third-Party
🗺️ Google Maps API → reverse geocoding
🤖 LLM API → summary + NLP
🔐 Security
🔒 HTTPS (TLS)
🔑 JWT / OAuth2
🛡️ Encryption (PII data)
🎙️ User consent for audio
🔄 Data Flow
🎤 Detect distress (AI / SOS)
📡 Send location + metadata
⚙️ Backend processes alert
🧠 NLP + summary generation
📢 Notify contacts
📍 Live tracking continues
🧠 Key Highlights
⚡ Edge + Cloud AI
🔄 Event-driven system
📈 Scalable (microservices)
🔐 Privacy-focused
