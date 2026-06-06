import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import Column, Integer, String, create_engine, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import declarative_base, sessionmaker

# This root app is its own project, so it reads .env from this same folder.
# load_dotenv must run before os.getenv(), otherwise DATABASE_URL will not be
# available to Python.
APP_DIR = Path(__file__).resolve().parent
load_dotenv(APP_DIR / ".env")


def get_database_url() -> str:
    """Return the PostgreSQL connection string used by SQLAlchemy."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        # This fallback keeps the app runnable during learning, but normally
        # you should define DATABASE_URL in .env.
        return "postgresql+psycopg2://localhost/testdb"

    return database_url


DATABASE_URL = get_database_url()

# The engine is SQLAlchemy's connection manager for the database.
engine = create_engine(DATABASE_URL)

# SessionLocal creates short-lived database sessions for each route.
SessionLocal = sessionmaker(bind=engine)

# Base is the parent class used by SQLAlchemy table models.
Base = declarative_base()


class Student(Base):
    """Python representation of the shared student database table."""

    __tablename__ = "student"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    age = Column(Integer, nullable=False)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run startup and shutdown tasks for FastAPI.

    FastAPI now recommends lifespan handlers instead of old event decorators.
    The code before yield runs before requests are accepted.
    The code after yield would run during shutdown.
    """
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Student CRUD App", lifespan=lifespan)


def render_page(title: str, body: str) -> HTMLResponse:
    """Build a very small HTML page without using templates."""
    html = f"""
    <html>
      <head>
        <title>{title}</title>
      </head>
      <body>
        <h1>{title}</h1>
        {body}
      </body>
    </html>
    """
    return HTMLResponse(content=html)


@app.get("/", response_class=HTMLResponse)
def home():
    body = """
      <ul>
        <li><a href='/students'>View all students</a></li>
        <li><a href='/students/new'>Add new student</a></li>
        <li><a href='/students/search'>Search students</a></li>
      </ul>
    """
    return render_page("Student CRUD Home", body)


@app.get("/students", response_class=HTMLResponse)
def list_students():
    # Open a session, read all student rows, then close the session.
    with SessionLocal() as session:
        students = session.execute(select(Student)).scalars().all()

    rows = ""
    for student in students:
        rows += f"<li>{student.id}: {student.name}, age {student.age} "
        rows += f"<a href='/students/{student.id}/edit'>Edit</a> "
        rows += f"<form style='display:inline' method='post' action='/students/{student.id}/delete'>"
        rows += "<button type='submit'>Delete</button></form></li>"

    body = f"""
      <p><a href='/'>Back to home</a></p>
      <p><a href='/students/new'>Add new student</a></p>
      <ul>{rows}</ul>
    """
    return render_page("All Students", body)


@app.get("/students/new", response_class=HTMLResponse)
def new_student_form():
    body = """
      <p><a href='/'>Back to home</a></p>
      <form method='post' action='/students/new'>
        <label>Name: <input type='text' name='name' required></label><br>
        <label>Age: <input type='number' name='age' required></label><br>
        <button type='submit'>Create Student</button>
      </form>
    """
    return render_page("Add New Student", body)


@app.post("/students/new")
def create_student(name: str = Form(...), age: int = Form(...)):
    with SessionLocal() as session:
        student = Student(name=name.strip(), age=age)
        session.add(student)
        try:
            # commit() permanently saves the new row.
            session.commit()
        except SQLAlchemyError as exc:
            # rollback() cancels the failed database change.
            session.rollback()
            raise HTTPException(status_code=500, detail=str(exc))

    return RedirectResponse(url="/students", status_code=303)


@app.get("/students/search", response_class=HTMLResponse)
def search_form():
    body = """
      <p><a href='/'>Back to home</a></p>
      <form method='get' action='/students/search/results'>
        <label>Student ID: <input type='number' name='student_id'></label><br>
        <label>Name contains: <input type='text' name='name'></label><br>
        <button type='submit'>Search</button>
      </form>
    """
    return render_page("Search Students", body)


@app.get("/students/search/results", response_class=HTMLResponse)
def search_results(student_id: int | None = None, name: str | None = None):
    with SessionLocal() as session:
        query = select(Student)
        if student_id is not None:
            query = query.filter(Student.id == student_id)
        elif name:
            query = query.filter(Student.name.ilike(f"%{name.strip()}%"))
        students = session.execute(query).scalars().all()

    if not students:
        body = f"<p>No students found.</p><p><a href='/students/search'>Back to search</a></p>"
    else:
        rows = "".join(
            f"<li>{student.id}: {student.name}, age {student.age} "
            f"<a href='/students/{student.id}/edit'>Edit</a></li>"
            for student in students
        )
        body = f"<p><a href='/students/search'>Back to search</a></p><ul>{rows}</ul>"
    return render_page("Search Results", body)


@app.get("/students/{student_id}/edit", response_class=HTMLResponse)
def edit_student_form(student_id: int):
    with SessionLocal() as session:
        student = session.get(Student, student_id)
        if student is None:
            raise HTTPException(status_code=404, detail="Student not found")

    body = f"""
      <p><a href='/students'>Back to list</a></p>
      <form method='post' action='/students/{student.id}/edit'>
        <label>Name: <input type='text' name='name' value='{student.name}' required></label><br>
        <label>Age: <input type='number' name='age' value='{student.age}' required></label><br>
        <button type='submit'>Update Student</button>
      </form>
    """
    return render_page("Update Student", body)


@app.post("/students/{student_id}/edit")
def update_student(student_id: int, name: str = Form(...), age: int = Form(...)):
    with SessionLocal() as session:
        student = session.get(Student, student_id)
        if student is None:
            raise HTTPException(status_code=404, detail="Student not found")
        student.name = name.strip()
        student.age = age
        try:
            session.commit()
        except SQLAlchemyError as exc:
            session.rollback()
            raise HTTPException(status_code=500, detail=str(exc))

    return RedirectResponse(url="/students", status_code=303)


@app.post("/students/{student_id}/delete")
def delete_student(student_id: int):
    with SessionLocal() as session:
        student = session.get(Student, student_id)
        if student is None:
            raise HTTPException(status_code=404, detail="Student not found")
        session.delete(student)
        try:
            session.commit()
        except SQLAlchemyError as exc:
            session.rollback()
            raise HTTPException(status_code=500, detail=str(exc))

    return RedirectResponse(url="/students", status_code=303)
