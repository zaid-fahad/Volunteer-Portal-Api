# 🌟 Volunteer Management System (VMApp - Backend)

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.2%2B-092e20?logo=django)](https://www.djangoproject.com/)
[![DRF](https://img.shields.io/badge/DRF-3.16%2B-red?logo=django)](https://www.django-rest-framework.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Supabase-336791?logo=postgresql)](https://supabase.com/)

A robust, enterprise-grade backend architecture built for managing community volunteer activities, real-time notifications, and high-impact events. This API serves as the central nervous system for the Volunteer Management System portal.

---

## 🏗️ Project Architecture

The system follows a modular, scalable monolithic architecture designed for clarity and decoupled development:

### **1. Core Modules**
- **`accounts`**: Custom User model handling multi-role authentication (Admin, Volunteer, Staff) using JWT.
- **`events`**: Complex event logic including registration, automatic attendance tracking, and capacity management.
- **`notifications`**: Real-time event-driven alert system integrated via `django-notifications-hq`.

### **2. Tech Stack Excellence**
- **Django Rest Framework (DRF)**: Utilizing ModelViewSets and Serializers for efficient, standardized API development.
- **Supabase (PostgreSQL)**: Leveraging cloud-native database performance with connection pooling.
- **SimpleJWT**: State-of-the-art stateless authentication.
- **Whitenoise**: Optimized production asset serving with Gzip/Brotli compression support.
- **Gunicorn**: Industrial-standard WSGI HTTP Server.

---

## ⚡ Quick Start & Installation

### **Prerequisites**
- Python 3.10 or higher
- PostgreSQL (or Supabase Connection String)

### **1. Local Environment Setup**
```bash
# Clone the repository
git clone https://github.com/mdrayhan03/Volunteer-Portal-Api.git
cd Volunteer-Portal-Api

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### **2. Configuration**
Create a `.env` file in the root directory:
```env
DEBUG=True
SECRET_KEY=your_secret_key_here
DATABASE_URL=postgresql://user:password@host:port/dbname
ALLOWED_HOSTS=localhost,127.0.0.1
```

### **3. Database Operations**
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

### **4. Launching the Engine**
```bash
python manage.py runserver
```

---

## 🚀 Deployment (Production)

The project is optimized for modern cloud platforms (Cloudflare Pages, Render, Heroku).

### **Build Script**
The provided `build.sh` automates the pipeline:
1. Installs latest production dependencies.
2. Performs zero-downtime database migrations (if `DATABASE_URL` is detected).
3. Executes `collectstatic` for optimal asset delivery.

### **Production Workflow**
```bash
chmod +x build.sh
./build.sh
gunicorn VMApp.wsgi:application
```

---

## 🛠️ Internal Tools & Logging
The backend includes a sophisticated **granulated logging system**:
- **`accounts.volunteer`**: Tracks volunteer signups and auth events.
- **`events.participation`**: Logs critical punching in/out metadata.
- **Rotation**: Automatic file rotation to prevent disk overflow in production.

---

## 🛡️ Security First
- Restricted CORS policy for frontend domain integrity.
- Custom middleware for header validation.
- Encrypted JWT tokens with configurable TTL.

Created with ❤️ for Community Impact.
