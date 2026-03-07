# Dataset & Annotation Specification

Purpose: Train the voice distress detection model and NLP modules.

Audio dataset (voice distress)
- Sources:
  - Public emotion corpora: RAVDESS, CREMA-D, SAVEE, IEMOCAP
  - In-house/crowdsourced simulated distress recordings (consent required)
- Recording specs:
  - Mono, 16kHz WAV
  - Recommended window length: 3s (sliding)
- Labels:
  - distress: {0,1}
  - severity: {1..5} (optional)
  - notes: noise type, background activity
- Augmentation:
  - Add real-world noises (traffic, subway, rain), reverberation, pitch shifts, clipping

NLP dataset
- Intent labels: report_incident, request_help, cancel_alert, false_alarm, info_request
- NER labels: LOCATION, PERSON, WEAPON, VEHICLE, TIME
- Example collection:
  - Simulated chat logs with diverse phrasing
  - Real-world anonymized transcripts (with consent)
- Languages:
  - Start with target locales; include locale-specific slang and transliteration cases

Annotation process
- Use an annotation tool (Label Studio, Prodigy)
- Provide annotators with clear guidelines and examples
- Inter-annotator agreement checks (Cohen’s kappa)

Privacy & ethics
- All participants must give informed consent
- Store PII separately or hashed
- Define retention policy for raw audio (e.g., delete after 30 days unless flagged)