# ScholarCashv2

## Project Purpose
ScholarCashv2 aims to provide a comprehensive platform for managing academic scholarships, helping students to discover, apply, and track scholarship opportunities efficiently.

## Features
- Search and filter scholarship opportunities
- User profiles for students and administrators
- Application tracking and notifications
- Admin dashboard for managing scholarships and users

## Installation
1. Clone the repository:
   
   ```bash
   git clone https://github.com/pyhcho099/ScholarCashv2.git
   ```
2. Navigate to the project directory:
   
   ```bash
   cd ScholarCashv2
   ```
3. Install the required dependencies:
   
   ```bash
   pip install -r requirements.txt
   ```

## Usage
- Start the application:
   
   ```bash
   python app.py
   ```
- Access the application in your web browser at `http://localhost:5000`.

## Project Structure
```
ScholarCashv2/
├── app.py                 # Main application file
├── models.py              # Data models
├── routes.py             # Application routes
├── templates/            # HTML templates
├── static/               # Static files (CSS, JS, images)
└── requirements.txt       # Python dependencies
```

## Technology Stack
- Python
- Flask
- SQLite
- HTML/CSS/JavaScript

## User Roles
- **Student**: Can search for scholarships, apply, and track their applications.
- **Administrator**: Can manage scholarships and monitor user activities.
