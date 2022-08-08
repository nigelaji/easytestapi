"""
接口表
用例表
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, DateTime, JSON, ForeignKey, String
from datetime import datetime
import inspect

try:
    config = __import__('config')
except ModuleNotFoundError:
    config = None

__all__ = ['engine', 'get_session', 'easytest_api_meta', 'easytest_case_meta', 'easytest_step_log']


default_db_config = dict(inspect.getmembers(config)).get('SQLALCHEMY_DATABASE_URI') or {}
default_db_config.update({"sqlite": "sqlite:///easytestapi.db"})

engine = create_engine(default_db_config.get("mysql") or default_db_config["sqlite"])
Base = declarative_base()


class easytest_api_meta(Base):
    __tablename__ = 'easytest_api_meta'
    id = Column(Integer, primary_key=True)  # 主键
    api_info = Column(JSON)
    update_time = Column(DateTime, default=datetime.now())

    def __init__(self, api_info):
        self.api_info = api_info

    def __repr__(self):
        return f"<Api:{self.id}>"


class easytest_case_meta(Base):
    __tablename__ = 'easytest_case_meta'
    case_id = Column(String, primary_key=True, nullable=False)   # 用例id
    api_id = Column(Integer)
    case = Column(JSON)
    update_time = Column(DateTime, default=datetime.now())

    def __init__(self, case_id, api_id, case_info):
        self.case_id = case_id
        self.api_id = api_id
        self.case_info = case_info

    def __repr__(self):
        return f"<Case:{self.case_id}>"


class easytest_step_log(Base):
    __tablename__ = 'easytest_step_log'
    id = Column(Integer, primary_key=True)  # 主键
    case_id = Column(String, nullable=False)   # 用例id
    step_index = Column(Integer, nullable=False)   # 步骤排序
    step_type = Column(String, nullable=False)   # 步骤类型
    step_info = Column(JSON)

    def __init__(self, case_id, step_index, step_type, step_info):
        self.case_id = case_id
        self.step_index = step_index
        self.step_type = step_type
        self.step_info = step_info

    def __repr__(self):
        return f"<Step:{self.id}>"


def get_session():
    session = sessionmaker(bind=engine)
    return session()


Base.metadata.create_all(engine)

# pip install mysqlclient
# print(engine.execute('select 1').fetchall())


