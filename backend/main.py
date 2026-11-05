import os, random
from datetime import datetime, timezone
from typing import Optional
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel, Field, Relationship, Session, create_engine, select, func

load_dotenv()
VIDEO_BUCKET = os.getenv("S3_VIDEO_BUCKET", "webpagemidterm")
THUMB_BUCKET = os.getenv("S3_THUMB_BUCKET", "webpagemidtermthumbnails")
REGION = os.getenv("AWS_REGION", "us-east-1")

def s3_url(bucket: str, key: str) -> str:
    return f"https://{bucket}.s3.{REGION}.amazonaws.com/{key}"

engine = create_engine("sqlite:///videos.db", connect_args={"check_same_thread": False})

class Video(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    description: str = ""
    category: str = Field(index=True)
    video_url: str       # URL completa del video en S3
    thumbnail_url: str   # URL completa de la miniatura en S3
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    comments: list["Comment"] = Relationship(back_populates="video")

class Comment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    video_id: int = Field(foreign_key="video.id", index=True)
    author: str
    text: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    video: Optional[Video] = Relationship(back_populates="comments")

class VideoOut(SQLModel):
    id: int
    title: str
    description: str
    category: str
    video_url: str
    thumbnail_url: str
    created_at: datetime
    comment_count: int = 0

class VideoCreate(SQLModel):
    title: str = Field(min_length=1, max_length=150)
    description: str = ""
    category: str = Field(min_length=1, max_length=50)
    video_url: str = Field(min_length=8, description="URL del video en S3")
    thumbnail_url: str = Field(min_length=8, description="URL de la miniatura en S3")

class CommentCreate(SQLModel):
    author: str = Field(min_length=1, max_length=40)
    text: str = Field(min_length=1, max_length=500)

class CommentOut(SQLModel):
    id: int
    video_id: int
    author: str
    text: str
    created_at: datetime

def to_out(v: Video) -> VideoOut:
    return VideoOut(id=v.id, title=v.title, description=v.description, category=v.category,
                    video_url=v.video_url, thumbnail_url=v.thumbnail_url,
                    created_at=v.created_at, comment_count=len(v.comments))

def get_session():
    with Session(engine) as s:
        yield s

@asynccontextmanager
async def lifespan(app: FastAPI):
    SQLModel.metadata.create_all(engine)
    yield

app = FastAPI(title="Video Platform API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5500", "http://127.0.0.1:5500"],
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

def get_video_or_404(video_id: int, s: Session) -> Video:
    v = s.get(Video, video_id)
    if not v:
        raise HTTPException(404, "Video no encontrado")
    return v

@app.get("/videos", response_model=list[VideoOut])
def list_videos(category: Optional[str] = None, q: Optional[str] = None,
                skip: int = 0, limit: int = Query(50, le=100), s: Session = Depends(get_session)):
    stmt = select(Video).order_by(Video.created_at.desc())
    if category:
        stmt = stmt.where(Video.category == category)
    if q:
        stmt = stmt.where(Video.title.ilike(f"%{q}%"))
    return [to_out(v) for v in s.exec(stmt.offset(skip).limit(limit)).all()]

@app.get("/categories", response_model=list[str])
def categories(s: Session = Depends(get_session)):
    return list(s.exec(select(Video.category).distinct().order_by(Video.category)).all())

@app.get("/videos/{video_id}", response_model=VideoOut)
def video_detail(video_id: int, s: Session = Depends(get_session)):
    return to_out(get_video_or_404(video_id, s))

@app.get("/videos/{video_id}/recommendations", response_model=list[VideoOut])
def recommendations(video_id: int, s: Session = Depends(get_session)):
    v = get_video_or_404(video_id, s)
    same = s.exec(select(Video).where(Video.category == v.category, Video.id != v.id)).all()
    return [to_out(x) for x in random.sample(same, min(10, len(same)))]

@app.get("/categories/{category}/random", response_model=list[VideoOut])
def random_by_category(category: str, s: Session = Depends(get_session)):
    vids = s.exec(select(Video).where(Video.category == category)).all()
    return [to_out(x) for x in random.sample(vids, min(10, len(vids)))]

@app.get("/videos/{video_id}/comments", response_model=list[CommentOut])
def get_comments(video_id: int, s: Session = Depends(get_session)):
    get_video_or_404(video_id, s)
    return s.exec(select(Comment).where(Comment.video_id == video_id)
                  .order_by(Comment.created_at.desc())).all()

@app.post("/videos/{video_id}/comments", response_model=CommentOut, status_code=201)
def add_comment(video_id: int, data: CommentCreate, s: Session = Depends(get_session)):
    get_video_or_404(video_id, s)
    c = Comment(video_id=video_id, author=data.author.strip(), text=data.text.strip())
    s.add(c); s.commit(); s.refresh(c)
    return c

@app.delete("/comments/{comment_id}", status_code=204)
def delete_comment(comment_id: int, s: Session = Depends(get_session)):
    c = s.get(Comment, comment_id)
    if not c:
        raise HTTPException(404, "Comentario no encontrado")
    s.delete(c); s.commit()

@app.post("/videos", response_model=VideoOut, status_code=201)
def create_video(data: VideoCreate, s: Session = Depends(get_session)):
    if not data.video_url.startswith("https://") or not data.thumbnail_url.startswith("https://"):
        raise HTTPException(422, "Las URLs deben empezar con https://")
    v = Video(**data.model_dump())
    s.add(v); s.commit(); s.refresh(v)
    return to_out(v)
