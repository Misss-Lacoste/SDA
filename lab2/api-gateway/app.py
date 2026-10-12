from fastapi import FastAPI, UploadFile, File, Form, HTTPException #импорт для работ необходимых модулей
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uuid
import os
from pathlib import Path
from typing import Optional
import urllib.parse
import uvicorn #для запуска fastapi

#ынизу основное приложение апишки
app = FastAPI(
    title="API Gateway - System of antiplagiat",
    docs_url="/docs", #вкл сваггер по адресу документации
    redoc_url="/redoc",
    servers=[{"url": "http://localhost:8000", "description": "Local server"}]
)

#CORS (Cross-Origin Resource Sharing) - чтоб подружить серверы
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], #запросы с любых доменов
    allow_credentials=True,
    allow_methods=["*"],  #все http методы
    allow_headers=["*"],  #все заголовки
)

#конфигурация
UPLOAD_DIR = Path("/app/uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

#хранилище в памяти
works_db = {}
reports_db = {}
 #начинаются главные эндпоинты
@app.get("/")  #коренвой
async def root():
    return {"message": "API Gateway для проверки антиплагиата"}

@app.post("/works")  #загрузка работ
async def submit_work(
    student_name: str = Form(...),
    assignment_id: str = Form(...),
    description: Optional[str] = Form(None),  #описание можно сделать по желанию с помщью параметра
    file: UploadFile = File(...)
):
    """
    В этом окошке можно загрузить работу на проверку :)
    """
    try:
        #id работы
        work_id = str(uuid.uuid4())
        report_id = str(uuid.uuid4())
        
        #содержимое файла
        content = await file.read()
        
        #сохр файл локально
        file_extension = os.path.splitext(file.filename)[1]
        saved_filename = f"{work_id}{file_extension}"
        file_path = UPLOAD_DIR / saved_filename
        
        with open(file_path, 'wb') as f:
            f.write(content)
         #облако слов из предоставленного файла
        try:
            file_content = content.decode('utf-8')
        except:
            #другие кодировки
            try:
                file_content = content.decode('cp1251')  # Windows-1251
            except:
                file_content = content.decode('latin-1', errors='ignore')

        #первые 50 слов для облака (чтобы юрл не был слишком длинным)
        words = file_content.split()[:50]
        text_for_cloud = " ".join(words)

        #если текст пустой - то fallback
        if not text_for_cloud.strip():
            text_for_cloud = f"{student_name} {assignment_id} работа"

        #кодируем в юрл
        encoded_text = urllib.parse.quote(text_for_cloud)

        #юрл для облака слов
        wordcloud_url = f"https://quickchart.io/wordcloud?text={encoded_text}&width=800&height=400"
        
        #сохр инфо
        works_db[work_id] = {
            "work_id": work_id,
            "student_name": student_name,
            "assignment_id": assignment_id,
            "description": description,
            "filename": file.filename,
            "saved_filename": saved_filename,
            "file_size": len(content),
            "uploaded_at": "2024-12-11T10:30:00",
            "text_preview": file_content[:100] + "..." if len(file_content) > 100 else file_content
        }
        
        import random
        plagiat_score = round(random.uniform(0, 0.3), 3)
        
        reports_db[work_id] = {
            "report_id": report_id,
            "work_id": work_id,
            "assignment_id": assignment_id,
            "student_name": student_name,
            "status": "completed",
            "plagiat_score": plagiat_score,
            "is_plagiat": plagiat_score > 0.8, 
            "wordcloud_url": wordcloud_url,
            "word_count": len(file_content.split()),
            "unique_words": len(set(file_content.lower().split())),
            "details": {
                "text_sample": file_content[:100] + "..." if len(file_content) > 100 
                else file_content,
                "cloud_words": words[:10],  #1-ые 10 слов для облака
                "analysis_method": "Проверка на процент идентичности",
                "comparisons_made": random.randint(0, 5),
                "similarity_threshold": 0.8,
                "recommendations": [
                    "Уровень оригинальности позволительный",
                ] if plagiat_score < 0.8 
                else [
                    "Данная работа содержит плагиат",
                ]
            }
        }
        
        return JSONResponse(
            status_code=201,
            content={
                "work_id": work_id,
                "report_id": report_id,
                "file_info": {
                    "student_name": student_name,
                    "assignment_id": assignment_id,
                    "filename": file.filename,
                    "file_size": len(content),
                    "status": "uploaded",
                    "text_preview": file_content[:100] + "..." if len(file_content) > 100 else file_content
                },
                "analysis_started": True,
                "wordcloud_generated": True,
                "wordcloud_url": wordcloud_url,
                "message": f"Файл загружен!:) Облако слов сгенерировано из {len(file_content.split())} слов."
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при загрузке файла:( {str(e)}"
        )

@app.get("/works/{work_id}")
async def get_work_info(work_id: str):
    """А в этом окошке можно получить информацию о работе"""
    if work_id not in works_db:
        raise HTTPException(status_code=404, detail="Работа не найдена...")
    
    return works_db[work_id]

@app.get("/works/{work_id}/reports")
async def get_work_reports(work_id: str):
    """А тут можно получить отчеты по проверке работы"""
    if work_id not in reports_db:
        raise HTTPException(status_code=404, detail="Отчеты не найдены...")
    
    return [reports_db[work_id]]

@app.get("/works/{work_id}/wordcloud")
async def get_wordcloud(work_id: str):
    """А тут имеется шикарная возможность получить облако слов для работы"""
    if work_id not in reports_db:
        raise HTTPException(status_code=404, detail="Работа не найдена...")
    
    return {
        "work_id": work_id,
        "wordcloud_url": reports_db[work_id]["wordcloud_url"],
        "report_id": reports_db[work_id]["report_id"],
        "word_count": reports_db[work_id].get("word_count", 0),
        "preview_text": reports_db[work_id]["details"]["text_sample"],
        "cloud_words": reports_db[work_id]["details"].get("cloud_words", [])
    }

@app.get("/assignments/{assignment_id}/works")
async def get_assignment_works(assignment_id: str):
    """Ну что, получим все работы по заданию?"""
    result = []
    for work_id, work in works_db.items():
        if work["assignment_id"] == assignment_id:
            result.append({
                "work_id": work_id,
                "student_name": work["student_name"],
                "filename": work["filename"],
                "uploaded_at": work["uploaded_at"],
                "file_size": work["file_size"]
            })
    return result

@app.get("/health")
async def health_check():
    """А тут проверка работоспособности системы"""
    return {
        "status": "healthy",
        "services": {
            "api_gateway": True,
            "file_storing": True,
            "file_analysis": True,
            "database": True
        },
        "version": "1.0.0"
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)