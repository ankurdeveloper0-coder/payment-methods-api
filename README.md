# Payment Methods API

A FastAPI-based backend for managing user payment methods (cards, UPI IDs, and bank accounts).  

This project demonstrates:

- Adding, retrieving, updating, and deleting payment methods.
- Handling multiple types: **Cards, UPI, and Banks**.
- Marking a payment method as **primary**.
- Data masking for sensitive information (cards & bank accounts).
- Preventing duplicate cards or UPI IDs.

---

## Features

- Add a credit/debit card (Visa, Mastercard, RuPay, Amex, Diners)  
- Add a UPI ID (PhonePe, Google Pay, Paytm, BHIM, Amazon Pay)  
- Add an Indian bank account (SBI, HDFC, ICICI, Axis, Kotak, PNB, etc.)  
- Retrieve all payment methods for a user  
- Retrieve a single payment method by ID  
- Set a payment method as primary  
- Delete a payment method  

---

## Note

- - **Authentication:** In this demo, authentication is skipped. `user_id` is passed directly. In production, JWT or OAuth2 would be used to secure endpoints, and `user_id` would come from the token.

## Tech Stack

- **Python 3.11**  
- **FastAPI** – API framework  
- **SQLAlchemy** – ORM for PostgreSQL  
- **PostgreSQL** – Database  
- **Pydantic** – Request/response validation  

---

## Installation

1. Clone the repository:

```bash
git clone https://github.com/ankurdeveloper0-coder/payment-methods-api.git

2. Create vitual environment 

python -m venv venv
source venv/bin/activate   # Linux/macOS

3. cd payment-methods-api


4. Install dependencies

    pip install -r requirements.txt


5.  Create a .env file 


DB_USER=username
DB_PASSWORD=password
DB_HOST=host
DB_PORT=5432
DB_NAME=


6.  Run the project 


uvicorn main:app --reload

6. APIS docs Avilable 


    http://127.0.0.1:8000/docs
