# TrikeGo

**Modern Ride-Hailing for Tricycle Transportation**

TrikeGo is a web-based ride-hailing platform designed to modernize tricycle operations through real-time booking, tracking, and fare guidance. The platform connects commuters with drivers, enabling efficient short-distance transportation while maintaining affordability and accessibility for local communities.

---

## 📋 Table of Contents

- [Tech Stack](#-tech-stack)
- [Prerequisites](#-prerequisites)
- [Setup & Installation](#-setup--installation)
- [Running the Application](#-running-the-application)
- [Project Structure](#-project-structure)
- [Team Members](#-team-members)
- [Contributing](#-contributing)
- [License](#-license)

## Tech Stack

| Component | Technology |
|-----------|-----------|
| **Backend** | Python with Django Framework |
| **Database** | PostgreSQL (hosted on Supabase) |
| **Frontend** | HTML5, CSS3, Vanilla JavaScript |
| **Version Control** | Git & GitHub |

---

## 📦 Prerequisites

Before you begin, ensure you have the following installed:
- Python 3.8 or higher
- pip (Python package manager)
- Git
- PostgreSQL (or Supabase account)

---

## ⚙️ Setup & Installation

### 1. Clone the Repository
```bash
git clone https://github.com/GIOnyx/CSIT327-G1-TrikeGo.git
cd TrikeGo
```
### 2. Create and Activate a Virtual Environment
For Windows:
```bash
python -m venv env
env\Scripts\activate
```
For macOS/Linux:
```bash
python3 -m venv env
source env/bin/activate
```
### 3. Install Dependencies
```bash
pip install -r requirements.txt
```
### 4. Apply Database Migrations
bashpython manage.py migrate
### 5. Create a Superuser (for Admin Access)
bashpython manage.py createsuperuser
Follow the prompts to set up your admin credentials.

### 6. Running the Application
Start the development server:
```bash
python manage.py runserver
```
The application will be available at: http://127.0.0.1:8000/

### Production: Redis (caching & Channels)

For production deployments we strongly recommend using Redis for Django caching and for Channels (WebSockets).

1. Provision a Redis instance (Render Redis addon, AWS Elasticache, or similar).
2. Set one of these environment variables in your host:
	- `DJANGO_CACHE_LOCATION` (preferred) — e.g. `redis://:password@redis-host:6379/0`
	- or `REDIS_URL` — same format.
3. (Optional) Tune `ROUTE_CACHE_TTL` in env to adjust how long route info is cached (default 15s).
4. Install dependencies and restart the app. The project will automatically use Redis when the env variable is present.

Local testing with Docker Compose (optional):

1. Start a local Redis container:

```powershell
docker run -d --name trikego-redis -p 6379:6379 redis:7-alpine
```

2. Set `DJANGO_CACHE_LOCATION=redis://127.0.0.1:6379/0` in `.env` (or export in your shell) and run the server.

Collect static files for production:

```powershell
python manage.py collectstatic --noinput
```

---
## Team Members

| Name | Role | CIT-U Email |
|-----------|-----------|-----------|
| **Badinas, Gregory Ivan Onyx M.** | Lead Developer | gregoryivanonyx.badinas@cit.edu |
| **Asia, Eron R.** | Developer | eron.asia@cit.edu |
| **Amoguis, Philma Jenica B.** | Developer | philmajenica.amoguis@cit.edu |
| **Betito, James Ruby P.** | Product Owner | jamesruby.betito@cit.edu |
| **Baldon, Kirsten Shane T.** | Business Analyst | kirstenshane.baldon@cit.edu |
| **Barangan, Mark Lorenz L.** | Scrum Master | marklorenz.barangan@cit.edu |

---
## License

This project is developed as part of CSIT327 coursework at Cebu Institute of Technology - University.

---
## Support

For questions or support, please contact the development team through the CIT-U emails listed above.
