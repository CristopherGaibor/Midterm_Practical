# Reproductor

Plataforma de videos Full Stack: FastAPI + SQLModel (SQLite) + AWS S3 + frontend HTML/CSS/JS.

## Requisitos
Python 3.10+, dos buckets S3 (videos y miniaturas) con lectura pública y CORS.

## Backend
```
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env   # completar bucket, región y claves
uvicorn main:app --reload
```
Documentación (Swagger): http://127.0.0.1:8000/docs

## Frontend
```
cd frontend
python -m http.server 5500
```
Abrir http://localhost:5500

## Agregar un video
1. Subir el video y la miniatura a S3 y copiar sus URLs.
2. En /docs usar `POST /videos` con título, categoría y las dos URLs.

(Carga masiva opcional: `python seed.py` con archivos en `backend/media/<categoria>/`.)
