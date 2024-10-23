This project is a web-based book listing platform where users can view books, search for specific titles or authors, and explore detailed information about each book. The application fetches data from an external API and displays it in a user-friendly interface.
Features
Displays a list of books fetched from an external API.
Search functionality to filter books by title or author.
Detailed view of each book, including the title, author, description, and other metadata.
Responsive design for various devices (mobile, tablet, desktop).
Technologies Used
Frontend:
HTML.
CSS: For styling the user interface (you can replace this with whatever you are using for styling).
Backend:
Python: Backend logic for handling API requests and processing data.
Flask.
Gunicorn: WSGI server for running the Python backend in production.
Database:
PostgreSQL: Relational database for storing book data.
SQLite: if you started with SQLite and converted it to PostgreSQL.
psycopg2: Python library to interact with PostgreSQL from the backend.
