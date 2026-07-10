# 🏥 Propsy Health

**Secure, GDPR-Compliant Google Health Data Synchronization & Research Platform**

[![Python](https://img.shields.io/badge/Python-3.12+-blue?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![MongoDB](<https://img.shields.io/badge/MongoDB-Motor%20Async-green?logo=mongodb>)](https://www.mongodb.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![Security](<https://img.shields.io/badge/Encryption-AES--256%20(Fernet)-red>)]()

Propsy Health is a privacy-first web application that allows users to securely synchronize their daily fitness, sleep, and heart rate metrics from **Google Health**. It provides a modern, interactive dashboard for visualizing personal health trends while strictly adhering to **GDPR**, **Informed Consent** standards, and **Google API Limited Use** requirements.

---

## ✨ Key Features

### Bank-Grade Security & Privacy

* **Encryption at Rest:** OAuth tokens and raw biometric data (heart rate samples, sleep stages) are encrypted using **AES-256 (Fernet)** before being written to MongoDB.
* **Encryption in Transit:** All communications are secured via TLS/SSL (HTTPS).
* **Session Validation:** Middleware automatically invalidates stale sessions if an admin deletes a user from the database.

### Interactive Health Dashboard

* **Real-Time Sync Progress:** Visual progress bar tracking background data synchronization from Google APIs.

### Strict Regulatory Compliance (Google & GDPR)

* **Informed Consent Flow:** Mandatory, versioned digital signature process with explicit checkboxes before accessing any data.
* **Data Portability (GDPR Art. 20):** One-click **JSON Export** of all raw, unmanipulated health records.
* **Right to Erasure (GDPR Art. 17):** Clear UI flows to permanently delete cached records and revoke Google OAuth tokens.
* **In-Product Privacy Notifications:** Prominent, persistent privacy banners explicitly stating how data is accessed, used, stored, and shared.

### Global & Accessible

* **i18n Support:** Full English and French translations across all templates.
* **Modern UI/UX:** Sober, health-focused design system using CSS Variables, responsive grids, and accessible contrast ratios.

---

## Tech Stack

| Category                    | Technology                                                |
| :-------------------------- | :-------------------------------------------------------- |
| **Backend Framework** | FastAPI, Starlette, Pydantic                              |
| **Database**          | MongoDB (via Motor Async Driver) / Google Cloud Firestore |
| **Authentication**    | Google OAuth 2.0, Session Cookies, CSRF Protection        |
| **Frontend**          | Jinja2 Templates, Vanilla JavaScript, Chart.js            |
| **Styling**           | Modern CSS3 (CSS Variables, Flexbox/Grid, Mobile-First)   |
| **Infrastructure**    | Docker, Docker Compose, Uvicorn (ASGI)                    |
| **Cryptography**      | `cryptography` library (Fernet / AES-256)               |

---

## Application Pages & User Flow

The application is structured to guide the user securely from onboarding to data management:

1. **Homepage (`index.html`):** A comprehensive landing page explaining the research study, features, and privacy commitments, featuring the official Google Sign-In button.
2. **Informed Consent (`consent.html`):** A mandatory, legally compliant form detailing the study's nature, risks, benefits, and data handling. Users must explicitly agree to three conditions before proceeding.
3. **Dashboard (`dashboard.html`):** The central control panel. Displays Account Information, Study Status, Data Download options, and critical actions like "Withdraw from Study" or "Disconnect".
4. **Health Data (`data.html`):** An interactive visualization page where users can select a date to view their steps, calories, heart rate, and sleep cycles.
5. **Privacy Policy (`privacy.html`):** A detailed, GDPR-compliant policy explicitly covering Google API Limited Use requirements.
6. **Withdrawal (`withdraw.html`):** A dedicated page providing instructions and direct email links for users to request manual data deletion and study withdrawal.

---

## Quick Start (Docker)

**1. Clone the Repository**
Download the project files to your local machine to get started.

**2. Configure Environment Variables**Create an environment file (`.env`) in the root directory based on the provided template. You will need to configure the following required variables:

* **MONGODB_URI:** Your MongoDB connection string.
* **SECRET_KEY:** A secure random string for session cookies.
* **ENCRYPTION_KEY:** A Fernet-compatible AES-256 key for data encryption.
* **GOOGLE_CLIENT_ID & GOOGLE_CLIENT_SECRET:** Your credentials from the Google Cloud Console.
* **ADMIN_PASSWORD:** The password for the secure admin dashboard.

**3. Run with Docker Compose**
Start the application using Docker Compose. Once the containers are built and running, the application will be available in your browser at `http://localhost:8080`.

---

## Data Export & Sync Engine

Propsy Health uses a **Database-First Export Strategy** to ensure lightning-fast data downloads and resilience against API rate limits.

* **Missing Date Detection:** The `SyncService` checks MongoDB for the last synced date to determine what data is missing.
* **Background Fetching:** It sequentially queries the Google Health API for the missing days, strictly respecting rate limits.
* **Real-Time Polling:** The frontend polls the sync-progress endpoint to update a visual progress bar in real-time.
* **Raw Export:** Once synced, the user can download a complete, unmanipulated JSON file containing all raw biometric data.

---

## Security & Compliance Details

### Google OAuth Verification Readiness

This application is built specifically to pass Google's strict OAuth verification process for sensitive health scopes:

* **Privacy Policy:** Hosted on the same domain, linked in the footer, navbar, and OAuth consent screen.
* **In-Product Notifications:** Contextual privacy banners on the Dashboard and Data pages.
* **Data Deletion Instructions:** Clear UI flows (Disconnect/Withdraw) and dedicated support emails for data removal.
* **Limited Use Disclosure:** Explicit statements in the Privacy Policy and Consent Form regarding Google API adherence.

### Admin Dashboard

A secure, password-protected admin panel allows researchers to:

* View system-wide statistics (Active consents, stored tokens, health records).
* Inspect decrypted audit logs (IP addresses, User-Agents).
* **Force Delete** a user's data across all collections (Consents, Tokens, Health Records) to handle urgent GDPR requests.

---

## 📄 License

Distributed under the MIT License. See the LICENSE file for more information.

<br>

<p align="center">
  <strong>Propsy Health</strong><br>
  <em>Empowering individuals with clear, actionable insights about their health data.</em><br>
  <a href="https://your-domain.com">Visit Live Demo</a> · 
  <a href="mailto:research@your-domain.com">Contact Research Team</a>
</p>
