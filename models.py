from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship # связь между полями
from database import Base

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    age = Column(Integer)
    gender = Column(String, index=True) # index=True, с помощью этого будет проще искать именно по этому параметру(в самой базе данных)

class Post(Base):
    __tablename__ = 'posts'

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    body = Column(String)
    author_id = Column(Integer, ForeignKey('users.id')) # ForeignKey, говорит о том что в качестве значения этого поля будет id какого либо определённого пользователя в табличке users

    author = relationship('User') # в этом поле будет вся информация о пользователе