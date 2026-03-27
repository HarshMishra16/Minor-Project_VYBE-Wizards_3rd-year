Minor-Project_VYBE-Wizards_3rd-year

🚨 AI-Powered Women Safety Application

This repository contains the specifications, prototypes, and deployment artifacts for an AI-powered women safety application that detects voice distress, supports NLP-based emergency chat, and generates concise emergency summaries.

🌟 Overview

The application is designed to provide real-time safety assistance by using AI to detect distress signals and automatically trigger emergency responses. It aims to enhance personal safety through intelligent monitoring and fast communication.

🔧 Core Components

📱 Mobile App (Flutter)

Audio capture
Local inference
Emergency chat interface

⚙️ Backend (FastAPI / Flask)

Alert system
NLP processing
AI-based emergency report generation

🤖 AI Models

Voice distress detection
Intent classification
Named Entity Recognition (NER)

🧪 Data & Annotation Pipelines

Dataset specifications
Data augmentation scripts
🧠 AI Emergency Summary

The system automatically generates a concise emergency report when distress is detected. This report is designed to help emergency responders quickly understand the situation.

Example Output:
{
  "summary": "User is in danger near MG Road, reporting harassment. Immediate help required.",
  "location": "28.4595, 77.0266",
  "time": "21:45",
  "distress_level": "high",
  "keywords": ["danger", "harassment", "help"]
}
🚀 Getting Started
Review architecture.md for system design
See dataset_spec.md for dataset collection and labeling
Use the fastapi/ and flutter/ folders (to be added) for backend and frontend implementation
🤝 Collaboration

This project is being developed with the vision of collaborating with Gurugram Police to enhance real-world safety response systems and enable faster emergency assistance.

🔐 Privacy & Legal
User consent is mandatory for audio monitoring

Raw audio data is:

Minimally stored
Encrypted for security

Designed following ethical AI and privacy-first principles

👨‍💻 Team

Team Members:
Harsh
Dhananjay
Pawan
Mukund

⭐ Contribution

Contributions are welcome. Feel free to fork the repository and submit pull requests.

📜 License

This project is licensed under the MIT License.
