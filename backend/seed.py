"""Sube a S3 los archivos de ./media y los registra en SQLite.
Estructura:  media/<categoria>/<nombre>.mp4  +  media/<categoria>/<nombre>.jpg
Uso: python seed.py"""
import os, pathlib, boto3
from dotenv import load_dotenv
from sqlmodel import SQLModel, Session, select
from main import engine, Video, VIDEO_BUCKET, THUMB_BUCKET, REGION, s3_url

load_dotenv()
s3 = boto3.client("s3", region_name=REGION)
SQLModel.metadata.create_all(engine)

with Session(engine) as db:
    for mp4 in sorted(pathlib.Path("media").glob("*/*.mp4")):
        cat, name = mp4.parent.name, mp4.stem
        thumb = mp4.with_suffix(".jpg")
        if not thumb.exists():
            print("Falta miniatura para", mp4); continue
        vkey, tkey = f"videos/{cat}/{mp4.name}", f"thumbs/{cat}/{thumb.name}"
        if db.exec(select(Video).where(Video.video_url == s3_url(VIDEO_BUCKET, vkey))).first():
            continue
        s3.upload_file(str(mp4), VIDEO_BUCKET, vkey, ExtraArgs={"ContentType": "video/mp4"})
        s3.upload_file(str(thumb), THUMB_BUCKET, tkey, ExtraArgs={"ContentType": "image/jpeg"})
        db.add(Video(title=name.replace("_", " ").title(), description=f"Video de {cat}",
                     category=cat, video_url=s3_url(VIDEO_BUCKET, vkey),
                     thumbnail_url=s3_url(THUMB_BUCKET, tkey)))
        db.commit(); print("OK", vkey)
