from fastapi import FastAPI, HTTPException, Depends
from typing import List
from sqlalchemy.orm import Session

from fastapi.middleware.cors import CORSMiddleware
from models import Base, User, Post
from Users_and_posts.database import  engine, session_local
from schemas import  UserCreate, User as DbUser, PostCreate, PostResponse # as, добавляет псевдоним(делаем это так как повторно импортируем User

app = FastAPI()

origins = [
    "http://localhost:8080",
    "http://127.0.0.1:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine) # создаём базу данных на основе того что есть

def get_db():
    db = session_local()    # создаём сессию
    try:                    # пробуем подключиться
        yield db
    finally:                # в независимости от результата закрываем соединение
        db.close()



@app.post('/users/', response_model=DbUser) # указываем конкретную модель в которой работаем
async def create_user(user: UserCreate, db: Session = Depends(get_db)) -> DbUser: # -> User, возвращаем нашего определённого пользователя
    db_user = User(name=user.name, age=user.age, gender=user.gender)
    db.add(db_user)
    db.commit() # добавляем коммит как раз в ручную
    db.refresh(db_user) # обновляем базу с учётом нового пользователя

    return db_user

@app.post('/posts/', response_model=PostResponse)
async def create_post(post: PostCreate, db: Session = Depends(get_db)) -> PostResponse:
    db_user = db.query(User).filter(User.id == post.author_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    db_post = Post(title=post.title, body=post.body, author_id=post.author_id)
    db.add(db_post)
    db.commit()
    db.refresh(db_post)

    return db_post


@app.get('/posts/', response_model=List[PostResponse]) # будет выводиться список из постов
async def posts(db: Session = Depends(get_db)) -> List[PostResponse]: # db: Session = Depends(get_db), параметр по подключению к базе данных
    return db.query(Post).all()

@app.get('/users/', response_model=List[DbUser])
async def users(db: Session = Depends(get_db)) -> List[DbUser]:
    return db.query(User).all()

@app.get('/users/{name}', response_model=DbUser)
async def users(name: str, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.name == name).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return db_user