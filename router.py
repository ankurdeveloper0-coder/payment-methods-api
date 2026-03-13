from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

import service as svc
from database import get_db
from schemas import (
    AddBankRequest,
    AddCardRequest,
    AddUPIRequest,
    IndianBank,
    SetPrimaryRequest,
)

router = APIRouter(prefix="/payment-methods", tags=["Payment Methods"])


@router.post(
    "/card", status_code=status.HTTP_201_CREATED, summary="Add a credit / debit card"
)
def add_card(req: AddCardRequest, db: Session = Depends(get_db)):
    """
    Accepts any Visa / Mastercard / RuPay / Amex / Diners card globally.
    - Card number Luhn-validated; only last4 stored
    - CVV validated but never stored
    - Network auto-detected from BIN
    """
    try:
        data = svc.add_card(db, req)
        return {
            "success": True,
            "message": f"{data['detail']['network'].title()} card ending {data['detail']['last4']} added",
            "data": data,
        }
    except HTTPException as e:
        raise e


@router.post("/upi", status_code=status.HTTP_201_CREATED, summary="Add a UPI ID")
def add_upi(req: AddUPIRequest, db: Session = Depends(get_db)):
    """
    Accepts any UPI ID — PhonePe, Google Pay, Paytm, BHIM, Amazon Pay, bank UPI.
    PSP is auto-resolved from the handle (e.g. @ybl → PhonePe).
    """
    try:
        data = svc.add_upi(db, req)
        return {
            "success": True,
            "message": f"UPI {data['detail']['upi_id']} added ({data['detail']['psp']})",
            "data": data,
        }
    except HTTPException as e:
        raise e


@router.post(
    "/bank", status_code=status.HTTP_201_CREATED, summary="Add an Indian bank account"
)
def add_bank(req: AddBankRequest, db: Session = Depends(get_db)):
    """
    Accepts any Indian bank — SBI, HDFC, ICICI, Axis, Kotak, PNB, etc.
    - IFSC validated; bank auto-detected from IFSC prefix
    - Account number confirmed (double entry) and masked in response
    """
    try:
        data = svc.add_bank(db, req)
        return {
            "success": True,
            "message": f"{data['detail']['bank_name']} account added",
            "data": data,
        }
    except HTTPException as e:
        raise e


@router.get("/banks/list", summary="List all supported Indian banks")
def list_banks():
    return {"banks": [b.value for b in IndianBank]}


@router.get("/{user_id}", summary="Get all payment methods for a user")
def get_methods(user_id: str, db: Session = Depends(get_db)):
    return {
        "success": True,
        "user_id": user_id,
        "data": svc.get_all_methods(db, user_id),
    }


@router.get("/{user_id}/{method_id}", summary="Get one payment method")
def get_one(user_id: str, method_id: str, db: Session = Depends(get_db)):
    return {"success": True, "data": svc.get_method_by_id(db, user_id, method_id)}


@router.patch("/primary", summary="Set a payment method as primary")
def set_primary(req: SetPrimaryRequest, db: Session = Depends(get_db)):
    return {"success": True, "data": svc.set_primary(db, req.user_id, req.method_id)}


@router.delete("/{user_id}/{method_id}", summary="Delete a payment method")
def delete_method(user_id: str, method_id: str, db: Session = Depends(get_db)):
    return svc.delete_method(db, user_id, method_id)
