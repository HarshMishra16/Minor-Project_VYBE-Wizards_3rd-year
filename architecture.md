# Architecture Overview

This document outlines the high-level architecture for the AI-Powered Women Safety Application.

Components:
- Mobile (Flutter)
  - Audio capture module
  - On-device feature extraction & lightweight model (optional)
  - Emergency UI and cancellation flow
  - Chat interface
- Backend (FastAPI)
  - Ingest alerts (/v1/alerts)
  - NLP endpoints (/v1/chat)
  - Summary generation (/v1/summary) — LLM orchestration
  - Notification & law-enforcement integration
- Datastore
  - MongoDB for events and logs
  - Short-lived caches for live tracking
- Third-party
  - Google Maps API for reverse geocoding
  - LLM provider for generative summaries

Security & Privacy:
- TLS for all comms
- JWT/OAuth2 for services
- Encryption-at-rest for PII
- Consent management for audio capture

Data flow:
1. Device continuously analyzes short audio windows for distress.
2. On detection (or user manual SOS), device sends minimal metadata and location to backend.
3. Backend records the alert, runs NLP on any text messages, generates a concise summary via LLM, and sends notifications to configured recipients.
4. Live location updates stream to the backend for responders.