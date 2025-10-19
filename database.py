from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship

DataBase = "sqlite:///broker.db"

Engine = create_engine(DataBase, connect_args={'check_same_thread': False})

Session = sessionmaker(bind=Engine)
Base = declarative_base()

def Get_db():
    db = Session()
    try:
        yield db
    finally:
        db.close()

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    surname = Column(String)

    portfolio_items = relationship("Portfolio", backref="users")

class Stock(Base):
    __tablename__ = 'stocks'

    id = Column(Integer, primary_key=True)
    stock_name = Column(String)
    company_name = Column(String)
    current_price = Column(Integer)

    portfolio_items = relationship("Portfolio", backref="stocks")

class Portfolio(Base):
    __tablename__ = 'portfolios'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    stock_id = Column(Integer, ForeignKey('stocks.id'))
    quantity = Column(Integer)

    user = relationship("User", backref="portfolios")
    stock = relationship("Stock", backref="portfolios")
