from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends
from fastapi.responses import FileResponse
from sqlalchemy import create_engine, Column, String, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
import uuid
import os
from pathlib import Path
from typing import Optional
import shutil  #копирование файлов

#создаем fastapi
app = FastAPI(title="File Storing Service")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:password@postgres:5432/antiplagiarism")
UPLOAD_DIR = Path("/app/uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

engine = create_engine(DATABASE_URL)  #движок для подключения к бд
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Work(Base):  #храним инфу о загруженных файлах
    __tablename__ = "works"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    #uuid - уникальный айди работы
    student_name = Column(String, nullable=False)
    assignment_id = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    filename = Column(String, nullable=False)
    filepath = Column(String, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    file_size = Column(String, nullable=True)
    mime_type = Column(String, nullable=True)

#таблицы
Base.metadata.create_all(bind=engine)

#наша любимая dependency injection
def get_db():
    db = SessionLocal()  #новая сессия
    try:
        yield db
    finally:
        db.close()

def save_upload_file(upload_file: UploadFile, work_id: str) -> str:
    """Сохраняет загруженный через fastapi файл"""
    file_extension = Path(upload_file.filename).suffix
    filename = f"{work_id}{file_extension}"
    filepath = UPLOAD_DIR / filename
    
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)
    
    return str(filepath)

#эндпоинты
@app.post("/files")
async def upload_file(
    student_name: str = Form(...),
    assignment_id: str = Form(...),
    description: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)  #к бд через dependency injection
):
    """Загрузить файл работы"""
    work_id = str(uuid.uuid4())
    
    filepath = save_upload_file(file, work_id)
    
    #сохр инфу в бд
    work = Work(
        id=work_id,
        student_name=student_name,
        assignment_id=assignment_id,
        description=description,
        filename=file.filename,
        filepath=filepath,
        file_size=str(file.size),
        mime_type=file.content_type
    )
    
    db.add(work)
    db.commit()
    db.refresh(work)
    
    return {
        "work_id": work_id,
        "student_name": student_name,
        "assignment_id": assignment_id,
        "filename": file.filename,
        "uploaded_at": work.uploaded_at.isoformat(),
        "status": "uploaded"
    }

@app.get("/files/{work_id}")
async def get_file_info(work_id: str, db: Session = Depends(get_db)):
    """Получить инфо о файле"""
    work = db.query(Work).filter(Work.id == work_id).first()
    if not work:
        raise HTTPException(status_code=404, detail="Work not found")
    
    return {
        "work_id": work.id,
        "student_name": work.student_name,
        "assignment_id": work.assignment_id,
        "description": work.description,
        "filename": work.filename,
        "uploaded_at": work.uploaded_at.isoformat(),
        "file_size": work.file_size,
        "mime_type": work.mime_type
    }

@app.get("/files/{work_id}/download")
async def download_file(work_id: str, db: Session = Depends(get_db)):
    """Скачать файл работы"""
    work = db.query(Work).filter(Work.id == work_id).first()
    if not work:
        raise HTTPException(status_code=404, detail="Work not found")
    
    if not os.path.exists(work.filepath):
        raise HTTPException(status_code=404, detail="File not found on server")
    
    return FileResponse(
        work.filepath,
        filename=work.filename,
        media_type=work.mime_type
    )

@app.get("/assignments/{assignment_id}/files")
async def get_assignment_files(assignment_id: str, db: Session = Depends(get_db)):
    """Получить все файлы по заданию"""
    works = db.query(Work).filter(Work.assignment_id == assignment_id).all()
    
    return [
        {
            "work_id": work.id,
            "student_name": work.student_name,
            "filename": work.filename,
            "uploaded_at": work.uploaded_at.isoformat()
        }
        for work in works
    ]

@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Health check"""
    try:
        db.execute("SELECT 1")
        return {"status": "healthy", "service": "file_storing"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)