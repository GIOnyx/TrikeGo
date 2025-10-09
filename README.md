# 🚖 TrikeGo

**TrikeGo** is a web ride-hailing platform that modernizes tricycle operations with real-time booking, tracking, and fare guidance.  
Commuters can request rides and view ETAs, while drivers get digital trip assignments and income tracking.  
Focused on **affordability** and **accessibility**, TrikeGo brings app-based convenience to local communities and improves short-distance transport efficiency.

---

## 🛠️ Tech Stack

- **Backend:** Python with the Django Framework  
- **Database:** PostgreSQL (hosted on Supabase)  
- **Frontend:** HTML5, CSS3, Vanilla JavaScript  
- **Version Control:** Git & GitHub  

---

## ⚙️ Setup & Run Instructions

### 1. Clone the Repository
```bash
git clone https://github.com/GIOnyx/CSIT327-G1-TrikeGo.git
cd TrikeGo
2. Create and Activate a Virtual Environment
For Windows

bash
python -m venv env
env\Scripts\activate
For macOS/Linux

bash
python3 -m venv env
source env/bin/activate
3. Install Dependencies
bash
pip install -r requirements.txt
4. Apply Database Migrations
bash
python manage.py migrate
5. Create a Superuser (for Admin Access)
bash
python manage.py createsuperuser
6. Run the Development Server
bash
python manage.py runserver
The application will be running at: 👉 http://127.0.0.1:8000/

👥 Team Members
Name	Role	CIT-U Email
Badinas, Gregory Ivan Onyx M.	Lead Developer	gregoryivanonyx.badinas@cit.edu
Asia, Eron R.	Developer	eron.asia@cit.edu
Amoguis, Philma Jenica B.	Developer	philmajenica.amoguis@cit.edu
Betito, James Ruby P.	Product Owner	jamesruby.betito@cit.edu
Baldon, Kirsten Shane T.	Business Analyst	kirstenshane.baldon@cit.edu
Barangan, Mark Lorenz L.	Scrum Master	marklorenz.barangan@cit.edu
