Minor-Project_VYBE-Wizards_3rd-year

🚨 AI-Powered Women Safety Application

This repository contains the specifications, prototypes, and deployment artifacts for an AI-powered women safety application that detects voice distress, supports NLP-based emergency chat, and generates concise emergency summaries.

🌟 Overview : 

The application is designed to provide real-time safety assistance by using AI to detect distress signals and automatically trigger emergency responses. It aims to enhance personal safety through intelligent monitoring and fast communication.

🔧 Core Components

📱 Mobile App(Flutter)

Audio  capture
Local inference
Emergency chat interface

⚙️ Backend(FastAPI / Flask)

Alert system
NLP processing
AI-based emergency report generation

🤖 AI Models

Voice distress detection
Intent classification
Named Entity Recognition (NER)

🧪 Data & Annotation Pipelines

Dataset specifications
Data augmentation scripts.
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

Team Members and Role :

1.)Harsh Kumar Mishra (Team Lead & Full Stack AI Developer)

a.)Led the overall project design and architecture
b.)Developed and integrated AI models for threat detection (weapons, suspicious activity)
c.)Built backend systems (APIs, real-time alerts, recording logic)
d.)Worked on frontend features including SOS trigger, live camera, and UI/UX
e.)Managed deployment, testing, and system integration

2.) Dhananjay Kumar – AI/ML Engineer

Assisted in training and optimizing computer vision models (YOLO/OpenCV)
Worked on improving detection accuracy and performance
Handled dataset preparation and preprocessing
Contributed to real-time detection pipeline integration

3.)Pawan Kumar 


4.) Mukund Thakur 
worked as a Full Stack Developer on the AI-powered Women Safety Application, contributing to both frontend and backend development. He designed and developed a responsive and user-friendly interface using modern web technologies, implementing features such as SOS alerts, live camera feed, and real-time notifications while ensuring strong user experience and accessibility. He also integrated the frontend with backend APIs and contributed to backend development by implementing case summary generation using LLM-based processing and handling server-side logic. Additionally, he worked on database design and management using MongoDB. The overall system was built using the MERN Stack, enabling seamless full-stack development and integration.

⭐ Contribution

Contributions are welcome. Feel free to fork the repository and submit pull requests.

📜 License

This project is licensed under the MIT License.
