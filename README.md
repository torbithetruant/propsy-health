
# Propsy Health

**Secure, GDPR-Compliant Google Health Data Synchronization & Research Platform**

[![Python](https://img.shields.io/badge/Python-3.12+-blue?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![MongoDB](<https://img.shields.io/badge/MongoDB-Motor%20Async-green?logo=mongodb>)](https://www.mongodb.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![Security](<https://img.shields.io/badge/Encryption-AES--256%20(Fernet)-red>)]()
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Propsy Health is a privacy-first web application that allows users to securely synchronize their daily fitness, sleep, and heart rate metrics from **Google Health**. It provides a modern, interactive dashboard for visualizing personal health trends while strictly adhering to **GDPR** and **Google API Limited Use** requirements.

---

## ✨ Key Features

### Bank-Grade Security & Privacy

* **Encryption at Rest:** OAuth tokens and raw biometric data (heart rate samples, sleep stages) are encrypted using **AES-256 (Fernet)** before being written to MongoDB.
* **Encryption in Transit:** All communications are secured via TLS/SSL (HTTPS).
* **Session Validation Middleware:** Automatically invalidates stale sessions if an admin deletes a user from the database.

### Retrieve Data From Google Health API

* **Real-Time Sync Progress:** Visual progress bar (`1/30`) tracking background data synchronization from Google APIs.

### Strict Regulatory Compliance (Google & GDPR)

* **Informed Consent Flow:** Mandatory, versioned digital signature process before accessing any data.
* **Data Portability (GDPR Art. 20):** One-click **JSON Export** of all raw, unmanipulated health records.
* **Right to Erasure (GDPR Art. 17):** Instant, permanent deletion of all cached records and automatic revocation of Google OAuth tokens.
* **In-Product Privacy Notifications:** Prominent, persistent privacy banners explicitly stating how data is accessed, used, stored, and shared.
* **Google API Limited Use:** Fully compliant with Google's strict User Data Policy.

### Global & Accessible

* **i18n Support:** Full English and French translations.
* **Modern UI/UX:** Sober, health-focused design system using CSS Variables, responsive grids, and accessible contrast ratios.

---

## Tech Stack

| Category                    | Technology                                                |
| :-------------------------- | :-------------------------------------------------------- |
| **Backend Framework** | FastAPI, Starlette, Pydantic                              |
| **Database**          | MongoDB (via Motor Async Driver) / Google Cloud Firestore |
| **Authentication**    | Google OAuth 2.0, Session Cookies, CSRF Protection        |
| **Frontend**          | Jinja2 Templates, Vanilla JavaScript                      |
| **Styling**           | Modern CSS3 (CSS Variables, Flexbox/Grid, Mobile-First)   |
| **Infrastructure**    | Docker, Docker Compose, Uvicorn (ASGI)                    |
| **Cryptography**      | `cryptography` library (Fernet / AES-256)               |

---

## 🏗️ Architecture & Project Structure

The codebase follows the **Service Layer Pattern**, ensuring clean separation between HTTP routing, business logic, and database operations.

```text
app/
├── api/                # FastAPI Routers (Auth, Dashboard, Admin, Consent)
├── core/               # Security, Encryption, Session Management, Templates
├── services/           # Business Logic (SyncService, ConsentStorage, HealthData)
├── auth/               # OAuth 2.0 Flow & Token Storage
├── static/             # CSS (Design System), JS, Images
├── templates/          # Jinja2 HTML (Modern, Responsive UI)
├── database.py         # Motor Connection & Index Initialization
├── config.py           # Pydantic Settings & Environment Variables
└── main.py             # FastAPI App Factory & Middleware Stack
```
