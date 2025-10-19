from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
import uvicorn

from database import Get_db, Engine, Base, User, Stock, Portfolio

class User_Create(BaseModel):
    name: str
    surname: str

class User_Response(BaseModel):
    id: int
    name: str
    surname: str

    model_config = ConfigDict(from_attributes=True)

class Stock_Create(BaseModel):
    stock_name: str
    company_name: str
    current_price: int

class Stock_Response(BaseModel):
    id: int
    stock_name: str
    company_name: str
    current_price: int

    model_config = ConfigDict(from_attributes=True)

class Portfolio_Item(BaseModel):
    stock_name: str
    company_name: str
    current_price: int
    quantity: int
    total_price: int

    model_config = ConfigDict(from_attributes=True)

class Portfolio_Response(BaseModel):
    user_id: int
    name: str
    portfolio_items: List[Portfolio_Item]
    total_portfolio_value: int
    average_stock_price: int

    model_config = ConfigDict(from_attributes=True)

class Add_To_Portfolio(BaseModel):
    stock_id: int
    quantity: int

Base.metadata.create_all(Engine)

App = FastAPI()

@App.post("/users", response_model=User_Response, tags=["Пользователь"], summary=["Регистрация пользователя"])
def create_user(user: User_Create, db: Session = Depends(Get_db)):
    db_user = User(name=user.name, surname=user.surname)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@App.get("/users", response_model=List[User_Response], tags=["Пользователь"],
         summary=["Зарегистрированные пользователи"])
def read_users(db: Session = Depends(Get_db)):
    users = db.query(User).all()
    return users

@App.put("/users", response_model=User_Response, tags=["Пользователь"], summary=["Обновление данных пользователя"])
def update_user(user_id: int, user_data: User_Create, db: Session = Depends(Get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if user is not None:
        user.name = user_data.name
        user.surname = user_data.surname
        db.commit()
        db.refresh(user)
        return user
    else:
        raise HTTPException(status_code=404, detail="User not found")

@App.delete("/users/{user_id}", tags=["Пользователь"], summary=['Удаление пользователя'])
def delete_user(user_id: int, db: Session = Depends(Get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if user is not None:
        db.delete(user)
        db.commit()
        return "Пользователь удален"
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

@App.post("/stocks", response_model=Stock_Response, tags=["Акции"], summary=["Добавление акции"])
def create_stock(stock: Stock_Create, db: Session = Depends(Get_db)):
    if db.query(Stock).filter(Stock.stock_name == stock.stock_name).first():
        raise HTTPException(status_code=404, detail="Stock not found")
    else:
        db_stock = Stock(stock_name=stock.stock_name, company_name=stock.company_name, current_price=stock.current_price)
        db.add(db_stock)
        db.commit()
        db.refresh(db_stock)
        return db_stock

@App.get("/stocks", response_model=List[Stock_Response],  tags=["Акции"], summary=["Добавленные акции"])
def read_stocks(db: Session = Depends(Get_db)):
    stocks = db.query(Stock).all()
    return stocks

@App.post("/users/{user_id}/portfolio", tags=["Портфель"], summary=["Добавить акции в портфель"])
def add_to_portfolio(user_id: int, portfolio_data: Add_To_Portfolio, db: Session = Depends(Get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")

    stock = db.query(Stock).filter(Stock.id == portfolio_data.stock_id).first()
    if not stock:
        raise HTTPException( status_code=status.HTTP_404_NOT_FOUND, detail="Акция не найдена")

    existing_item = db.query(Portfolio).filter(Portfolio.user_id == user_id, Portfolio.stock_id == portfolio_data.stock_id).first()

    if existing_item:
        existing_item.quantity += portfolio_data.quantity
    else:
        new_item = Portfolio( user_id=user_id, stock_id=portfolio_data.stock_id, quantity=portfolio_data.quantity)
        db.add(new_item)

    db.commit()
    return stock.stock_name,"Добавлен в портфель"

@App.get("/users/{user_id}/portfolio", response_model=Portfolio_Response, tags=["Портфель"], summary="Получить портфель пользователя")
def get_portfolio(user_id: int, db: Session = Depends(Get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")

    portfolio_items = db.query(Portfolio).filter(Portfolio.user_id == user_id).all()
    portfolio_data = []
    total_portfolio_value = 0
    total_quantity = 0

    for item in portfolio_items:
        stock = db.query(Stock).filter(Stock.id == item.stock_id).first()
        if stock:
            item_value = stock.current_price * item.quantity
            total_portfolio_value += item_value
            total_quantity += item.quantity

            portfolio_data.append({
                "stock_name": stock.stock_name,
                "company_name": stock.company_name,
                "current_price": stock.current_price,
                "quantity": item.quantity,
                "total_price": item_value
            })

    if total_quantity > 0:
        average_stock_price = total_portfolio_value / total_quantity
    else:
        average_stock_price = 0

    return {
        "user_id": user.id,
        "name": user.name,
        "portfolio_items": portfolio_data,
        "total_portfolio_value": int(total_portfolio_value),
        "average_stock_price": int(average_stock_price)
    }

@App.delete("/users/{user_id}/portfolio/{stock_id}", tags=["Портфель"], summary="Удалить акции из портфеля")
def remove_from_portfolio(user_id: int, stock_id: int, quantity: int = 1, db: Session = Depends(Get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")

    portfolio_item = db.query(Portfolio).filter(Portfolio.user_id == user_id, Portfolio.stock_id == stock_id).first()

    if not portfolio_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Акция не найдена в портфеле")

    stock = db.query(Stock).filter(Stock.id == stock_id).first()

    if portfolio_item.quantity <= quantity:
        db.delete(portfolio_item)
        message = stock.stock_name, "удален из портфеля"
    else:
        portfolio_item.quantity -= quantity
        message = stock.stock_name, "удалены из портфеля"

    db.commit()
    return message

if __name__ == "__main__":
    uvicorn.run("main:App", host="0.0.0.0", port=8000, reload=False)


