# Propsy Health OAuth Connector

Secure FastAPI application for Google Health (formerly Fitbit) OAuth authentication with MongoDB storage.

## 🎯 Purpose

- Authenticate users with Google OAuth 2.0
- Obtain Google Health API tokens with required scopes
- Retrieve Google Health identity via `get_legacy_user_id()`
- Store tokens securely in MongoDB for later API usage

## 🚀 Quick Start

### 1. Prerequisites

```bash
# Python 3.12+
python3.12 --version

# MongoDB running locally or accessible via URI
mongod --version

# Virtual environment
python3.12 -m venv venv
source venv/bin/activate