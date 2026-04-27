# GatePlate Backend

GatePlate is an Automatic License Plate Recognition (ALPR) system and access control management application. This repository contains the backend built with Django, Django Channels, and PyTorch (YOLO).

## Features
- **License Plate Recognition:** Uses a YOLO-based custom vision engine to detect and recognize vehicle plates from photo and video streams.
- **Real-time System Monitoring:** Streams server CPU and RAM metrics to the frontend using WebSockets (Django Channels) and `psutil`.
- **Access Control:** Manage registered employee vehicles and temporary guest access.
- **Monetization & API Keys:** Integrated with the WayForPay payment gateway to issue API keys for users who exceed their free usage limits.

## Tech Stack
- **Framework:** Django & Django REST Framework
- **WebSockets:** Django Channels
- **Machine Learning:** PyTorch, YOLO, OpenCV
- **Database:** SQLite (default)

## Installation & Setup

1. **Create and activate a virtual environment:**
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # macOS/Linux:
   source .venv/bin/activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Apply database migrations:**
   ```bash
   python manage.py migrate
   ```

4. **Run the development server:**
   ```bash
   python manage.py runserver
   ```

## Testing & Quality
This project uses `pytest`, `flake8`, `black`, and `bandit` for CI/CD.
Run tests locally using:
```bash
pytest --cov=. --cov-report=html
```
