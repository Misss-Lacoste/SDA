from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from sqlalchemy import create_engine, Column, String, DateTime, Text, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
import uuid
import os
import httpx
from typing import List, Optional
from pydantic import BaseModel
import json

from plagiarism_checker import PlagiarismChecker

app = FastAPI(title="File Analysis Service")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:password@postgres:5432/antiplagiat")
FILE_STORING_SERVICE_URL = os.getenv("FILE_STORING_SERVICE_URL", "http://file-storing-service:8000")

#бд
engine = create_engine(DATABASE_URL)  #движок для sqlalchemy
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class AnalysisReport(Base):
    __tablename__ = "analysis_reports"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    work_id = Column(String, nullable=False)
    assignment_id = Column(String, nullable=False)
    student_name = Column(String, nullable=False)
    status = Column(String, nullable=False)
    plagiat_score = Column(Float, nullable=True)
    is_plagiat = Column(Boolean, nullable=True)
    report_data = Column(Text, nullable=True)
    analyzed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    wordcloud_url = Column(String, nullable=True)

#таблицы
Base.metadata.create_all(bind=engine)

#наша любимая dependency injection
def get_db():
    db = SessionLocal()  #созд новую сессию
    try:
        yield db  #обработчик запроса
    finally:
        db.close()

class ReportResponse(BaseModel):
    report_id: str
    work_id: str
    status: str
    plagiat_score: Optional[float] = None
    is_plagiat: Optional[bool] = None
    analyzed_at: Optional[str] = None
    wordcloud_url: Optional[str] = None

async def download_work_file(work_id: str) -> Optional[str]:
    """Скачивание файла для оценки на уровень плагиата"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{FILE_STORING_SERVICE_URL}/files/{work_id}/download",
                timeout=30.0
            )
            if response.status_code == 200:
                #сохр временный файл
                temp_filename = f"/tmp/{work_id}_temp"
                with open(temp_filename, "wb") as f:
                    f.write(response.content)
                return temp_filename
        except Exception as e:
            print(f"Ошибка загрузки файла:( {e}")
            return None

async def get_work_info(work_id: str):
    """Получение информацию о работе"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{FILE_STORING_SERVICE_URL}/files/{work_id}",
                timeout=10.0
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Ошибка получения инфы: {e}")
            return None

async def get_assignment_works(assignment_id: str) -> List[dict]:
    """Получение всех работы по заданию"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{FILE_STORING_SERVICE_URL}/assignments/{assignment_id}/files",
                timeout=10.0
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Ошибка: {e}")
            return []

def generate_wordcloud_url(text: str) -> str:
    """Генерация облака слов"""
    import urllib.parse
    
    words = text.split()[:50]  #первые 50 слов для облака
    text_for_cloud = " ".join(words)
    
    params = {  #красиво задаем параметры
        "text": text_for_cloud,
        "width": 800,
        "height": 400,
        "colors": "['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']",
        "fontScale": 30,
        "scale": "linear",
        "rotation": 0.5,
        "padding": 2
    }
    
    query_string = urllib.parse.urlencode(params)
    return f"https://quickchart.io/wordcloud?{query_string}"

async def analyze_work_background(work_id: str, report_id: str):
    """Задача анализа работы на плагиат"""
    db = SessionLocal()
    
    try:
        #обновл статус на processing
        report = db.query(AnalysisReport).filter(AnalysisReport.id == report_id).first()
        report.status = "processing"
        db.commit()
        work_info = await get_work_info(work_id)
        if not work_info:
            report.status = "failed"
            db.commit()
            return
        
        assignment_id = work_info["assignment_id"]
        
        #скачиваем файл
        file_path = await download_work_file(work_id)
        if not file_path:
            report.status = "failed"
            db.commit()
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except:
            with open(file_path, 'r', encoding='latin-1') as f:
                content = f.read()
        
        all_works = await get_assignment_works(assignment_id)
        
        previous_works_content = []
        previous_work_ids = []
        
        for work in all_works:
            if work["work_id"] != work_id:  #скачиваем предыд работу
                prev_file_path = await download_work_file(work["work_id"])
                if prev_file_path:
                    try:
                        with open(prev_file_path, 'r', encoding='utf-8') as f:
                            prev_content = f.read()
                            previous_works_content.append(prev_content)
                            previous_work_ids.append(work["work_id"])
                    except:
                        try:
                            with open(prev_file_path, 'r', encoding='latin-1') as f:
                                prev_content = f.read()
                                previous_works_content.append(prev_content)
                                previous_work_ids.append(work["work_id"])
                        except:
                            pass
        
         #самое важное - проверка на плагиат
        checker = PlagiarismChecker()
        plagiat_result = checker.check_plagiat(content, previous_works_content)
        
        #облако слов
        wordcloud_url = generate_wordcloud_url(content)
        
        #отчет
        report.status = "completed"
        report.plagiat_score = plagiat_result["similarity_score"]
        report.is_plagiat = plagiat_result["is_plagiat"]
        report.report_data = json.dumps(plagiat_result)
        report.analyzed_at = datetime.utcnow()
        report.wordcloud_url = wordcloud_url
        db.commit()
        
        #очищаем временные файлы
        try:
            os.remove(file_path)
            for work_id in previous_work_ids:
                temp_file = f"/tmp/{work_id}_temp"
                if os.path.exists(temp_file):
                    os.remove(temp_file)
        except:
            pass
            
    except Exception as e:
        print(f"Ошибка в фоновом анализе:( {e}")
        if db:
            report = db.query(AnalysisReport).filter(AnalysisReport.id == report_id).first()
            if report:
                report.status = "failed"
                db.commit()
    finally:
        db.close()

#эндпоинты
 #загрузка файла
@app.post("/works/{work_id}/analyze")
async def analyze_work(work_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Запустить анализ работы на плагиат"""
    #инфо о работе
    work_info = await get_work_info(work_id)
    if not work_info:
        raise HTTPException(status_code=404, detail="Работа не найдена...")
    
    #отчетесть или нет
    existing_report = db.query(AnalysisReport).filter(AnalysisReport.work_id == work_id).first()
    if existing_report:
        if existing_report.status == "processing":
            raise HTTPException(status_code=400, detail="Анализ в процессе")
        elif existing_report.status == "completed":
            return {
                "message": "Aнализ почти завершен",
                "report_id": existing_report.id
            }
    
    #новый отчет
    report = AnalysisReport(
        work_id=work_id,
        assignment_id=work_info["assignment_id"],
        student_name=work_info["student_name"],
        status="pending"
    )
    
    db.add(report)
    db.commit()
    db.refresh(report)
    
    #запускаем задачу
    background_tasks.add_task(analyze_work_background, work_id, report.id)
    
    return {
        "message": "Анализ в работе",
        "report_id": report.id,
        "work_id": work_id,
        "status": "pending"
    }

@app.get("/works/{work_id}/reports")
async def get_work_reports(work_id: str, db: Session = Depends(get_db)):
    """Получить отчеты по проверке работы"""
    reports = db.query(AnalysisReport).filter(AnalysisReport.work_id == work_id).all()
    
    if not reports:
        raise HTTPException(status_code=404, detail="Отчеты не найдены")
    
    return [
        ReportResponse(
            report_id=report.id,
            work_id=report.work_id,
            status=report.status,
            plagiat_score=report.plagiat_score,
            is_plagiat=report.is_plagiat,
            analyzed_at=report.analyzed_at.isoformat() if report.analyzed_at else None,
            wordcloud_url=report.wordcloud_url
        ).dict()
        for report in reports
    ]

@app.get("/reports/{report_id}")
async def get_report(report_id: str, db: Session = Depends(get_db)):
    """Получить детальный отчет"""
    report = db.query(AnalysisReport).filter(AnalysisReport.id == report_id).first()
    
    if not report:
        raise HTTPException(status_code=404, detail="Отчет не найден")
    
    result = {
        "report_id": report.id,
        "work_id": report.work_id,
        "assignment_id": report.assignment_id,
        "student_name": report.student_name,
        "status": report.status,
        "plagiat_score": report.plagiat_score,
        "is_plagiat": report.is_plagiat,
        "analyzed_at": report.analyzed_at.isoformat() if report.analyzed_at 
        else 
        None,
        "wordcloud_url": report.wordcloud_url,
        "created_at": report.created_at.isoformat()
    }
    
    if report.report_data:
        try:
            result["details"] = json.loads(report.report_data)
        except:
            result["details"] = report.report_data
    
    return result

@app.get("/works/{work_id}/wordcloud")
async def get_wordcloud(work_id: str, db: Session = Depends(get_db)):
    """Получить URL для облака слов"""
    report = db.query(AnalysisReport).filter(
        AnalysisReport.work_id == work_id,
        AnalysisReport.status == "completed"
    ).first()
    
    if not report or not report.wordcloud_url:
        raise HTTPException(status_code=404, detail="Облако слов недоступно")
    
    return {
        "work_id": work_id,
        "wordcloud_url": report.wordcloud_url,
        "report_id": report.id
    }

@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Health checking"""
    try:
        db.execute("SELECT 1")
        return {"status": "healthy", "service": "file_analysis"}
    except Exception as e:  #если не удалось - сервис не в порядке
        raise HTTPException(status_code=503, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)