from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SQLDB_URL = 'sqlite:///./database.db'

engine = create_engine(SQLDB_URL, connect_args={'check_same_thread': False}) # отключает ограничение подключения с различных потоков

session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine) # при помощи этого сохраняем всё в базу в ручном режиме

Base = declarative_base() # эта функция создаст базовый класс из моделей из которых позже будут созданы таблицы в базе данных


