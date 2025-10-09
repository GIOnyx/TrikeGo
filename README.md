# TrikeGo

TrikeGo is a web ride-hailing platform that modernizes tricycle operations with real-time booking, tracking, and fare guidance. Commuters can request rides and view ETAs, while drivers get digital trip assignments and income tracking. Focused on affordability and accessibility, TrikeGo brings app-based convenience to local communities and improves short-distance transport efficiency.

---

Tech Stack Used
Backend: Python with the Django Framework
Database: PostgreSQL (hosted on Supabase)
Frontend: HTML5, CSS3, Vanilla Javascript
Version Control: Git & GitHub

---

Setup & Run Instructions
Clone the Repository

git clone https://github.com/GIOnyx/CSIT327-G1-TrikeGo.git
cd TrikeGo


Create and Activate a Virtual Environment

# For Windows
python -m venv env
env\Scripts\activate

# For macOS/Linux
python3 -m venv env
source env/bin/activate


Install Dependencies

This command installs all the necessary Python packages.
pip install -r requirements.txt


Apply Database Migrations

This command will set up the database schema. The project is configured to use the .env file provided by the team.
python manage.py migrate


Create a Superuser (for Admin Access)

This step is required to access the Django admin panel at /admin/.
python manage.py createsuperuser


Run the Development Server

python manage.py runserver


The application will be running at http://122.0.0.1:8000/.

---

Team Members<br>
Name    Role    CIT-U Email<br>
Badinas Gregory Ivan Onyx M. | Lead Developer | gregoryivanonyx.badinas@cit.edu<br>
Asia, Eron R. | Developer | eron.asia@cit.edu<br>
Amoguis, Philma Jenica B. | Developer | philmajenica.amoguis@cit.edu<br>
Betito, James Ruby P. | Product Owner | jamesruby.betito@cit.edu<br>
Baldon, Kirsten Shane T. | Business Analyst | kirstenshane.baldon@cit.edu<br>
Barangan, Mark Lorenz L.  | Scrum Master | marklorenz.barangan@cit.edu
