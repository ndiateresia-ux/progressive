# School Results Management System

A Django-based web application for managing academic results.  
It supports role-based access for **teachers** and **students**, subject/class assignments, results upload, filtering, and PDF export.

---

## 🚀 Features

- Teacher subject registration (assign subjects to classes).
- Upload and manage student marks.
- Student and teacher portals with filters (subject, class, semester).
- PDF export of results (teachers and students).
- Role-based dashboards (teacher vs student).
- Analytics dashboard (average scores, trends, comparisons).

---

## 🛠️ Tech Stack

- **Backend**: Django 5.0, Python 3.12
- **Frontend**: Bootstrap 5, custom templates
- **Database**: SQLite (default), can be swapped for PostgreSQL/MySQL
- **PDF Generation**: `xhtml2pdf` or `reportlab`

---

## 📦 Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/school-results.git
   cd school-results
2. Create and activate a virtual environment:
   python -m venv venv
   source venv/bin/activate   # Linux/Mac
   venv\Scripts\activate      # Windows
3. Install dependencies:
    pip install -r requirements.txt
4. Run migrations:
    python manage.py migrate
5. Create a superuser:
    python manage.py createsuperuser
6. Start the development server:
    python manage.py runserver
📂 Project Structure
Code
progressive_app/
│
├── models.py          # User, Subject, SchoolClass, Marks, TeacherSubject
├── views.py           # Teacher & Student portals, PDF exports
├── urls.py            # Routes
├── templates/
│   ├── teachers/      # Teacher views & PDFs
│   ├── students/      # Student views & PDFs
│   └── base.html      # Shared layout
└── static/            # Bootstrap, icons, custom CSS
📖 Usage
Teachers:

Register subjects and classes

Upload marks for students

View results with filters

Export results to PDF

Students:

View their own results

Filter by subject, class, semester

Download results as PDF

📊 Analytics
Teachers and students can view performance trends:

Average scores by subject/class

Score trends by semester

Top performers

📸 Screenshots
Teacher Portal

Student Portal

Analytics Dashboard
<img width="1500" height="868" alt="Screenshot 2025-12-08 113338" src="https://github.com/user-attachments/assets/fde722ea-a63a-4df5-afcc-8d6842643699" />

🤝 Contributing
Fork the repo

Create a feature branch<img width="1899" height="646" alt="Screenshot 2025-12-08 113745" src="https://github.com/user-attachments/assets/b6507cf7-9b87-462e-a7b5-838af006347c" />


Commit changes

Open a pull request<img width="1892" height="867" alt="Screenshot 2025-12-08 113918" src="https://github.com/user-attachments/assets/059d07b4-3158-49be-bcf9-6130a83fc436" />

