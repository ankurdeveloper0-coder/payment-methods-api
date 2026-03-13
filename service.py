import re
import uuid
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from models import (
    AccountType,
    BankDetail,
    CardDetail,
    CardNetwork,
    PaymentMethodType,
    UPIDetail,
    UserPaymentMethod,
)
from schemas import KNOWN_UPI_PSPS, AddBankRequest, AddCardRequest, AddUPIRequest


def _gen_id():
    return str(uuid.uuid4())


def _clear_primary(db: Session, user_id: str):
    db.query(UserPaymentMethod).filter(UserPaymentMethod.user_id == user_id).update(
        {"is_primary": False}
    )


def _detect_network(n: str) -> CardNetwork:
    if n.startswith("4"):
        return CardNetwork.VISA
    if re.match(r"^5[1-5]|^2[2-7]", n):
        return CardNetwork.MASTERCARD
    if re.match(r"^6", n):
        return CardNetwork.RUPAY
    if re.match(r"^3[47]", n):
        return CardNetwork.AMEX
    if re.match(r"^3[0689]", n):
        return CardNetwork.DINERS
    return CardNetwork.UNKNOWN


def _resolve_psp(upi_id: str) -> str:
    handle = upi_id.split("@")[-1].lower() if "@" in upi_id else ""
    return KNOWN_UPI_PSPS.get(handle, f"@{handle}")


def _mask_account(n: str) -> str:
    blocks = ["•" * 4 for _ in range((len(n) - 4) // 4)]
    return " ".join(blocks) + " " + n[-4:]


def _serialize(pm: UserPaymentMethod) -> dict:
    base = {
        "id": pm.id,
        "type": pm.type,
        "is_primary": pm.is_primary,
        "nickname": pm.nickname,
        "created_at": pm.created_at.isoformat() + "Z",
    }
    if pm.type == PaymentMethodType.CARD and pm.card:
        base["detail"] = {
            "last4": pm.card.last4,
            "card_holder_name": pm.card.card_holder_name,
            "expiry_month": pm.card.expiry_month,
            "expiry_year": "**",
            "network": pm.card.network,
        }
    elif pm.type == PaymentMethodType.UPI and pm.upi:
        base["detail"] = {"upi_id": pm.upi.upi_id, "psp": pm.upi.psp}
    elif pm.type == PaymentMethodType.BANK and pm.bank:
        base["detail"] = {
            "account_holder_name": pm.bank.account_holder_name,
            "masked_account": pm.bank.masked_account,
            "ifsc_code": pm.bank.ifsc_code,
            "bank_name": pm.bank.bank_name,
            "account_type": pm.bank.account_type,
        }
    return base


def add_card(db: Session, req: AddCardRequest) -> dict:
    existing_card = (
        db.query(CardDetail)
        .join(UserPaymentMethod, CardDetail.payment_method_id == UserPaymentMethod.id)
        .filter(
            UserPaymentMethod.user_id == req.user_id,
            CardDetail.last4 == req.card_number[-4:],
        )
        .first()
    )

    if existing_card:
        raise HTTPException(status_code=409, detail="Card already exists for this user")

    # Existing logic
    if req.make_primary:
        _clear_primary(db, req.user_id)

    pm = UserPaymentMethod(
        id=_gen_id(),
        user_id=req.user_id,
        type=PaymentMethodType.CARD,
        is_primary=req.make_primary,
        nickname=req.nickname,
    )
    db.add(pm)
    db.flush()

    db.add(
        CardDetail(
            id=_gen_id(),
            payment_method_id=pm.id,
            last4=req.card_number[-4:],
            card_holder_name=req.card_holder_name,
            expiry_month=req.expiry_month,
            expiry_year=req.expiry_year,
            network=_detect_network(req.card_number),
        )
    )

    db.commit()
    db.refresh(pm)
    return _serialize(pm)


def add_upi(db: Session, req: AddUPIRequest) -> dict:

    existing_upi = (
        db.query(UPIDetail)
        .join(UserPaymentMethod)
        .filter(
            UserPaymentMethod.user_id == req.user_id, UPIDetail.upi_id == req.upi_id
        )
        .first()
    )

    if existing_upi:
        raise HTTPException(status_code=409, detail="UPI already exists for this user")

    if req.make_primary:
        _clear_primary(db, req.user_id)

    pm = UserPaymentMethod(
        id=_gen_id(),
        user_id=req.user_id,
        type=PaymentMethodType.UPI,
        is_primary=req.make_primary,
        nickname=req.nickname,
    )

    db.add(pm)
    db.flush()

    db.add(
        UPIDetail(
            id=_gen_id(),
            payment_method_id=pm.id,
            upi_id=req.upi_id,
            psp=_resolve_psp(req.upi_id),
        )
    )

    db.commit()
    db.refresh(pm)
    return _serialize(pm)


def add_bank(db: Session, req: AddBankRequest) -> dict:

    existing_bank = (
        db.query(BankDetail)
        .join(UserPaymentMethod)
        .filter(
            UserPaymentMethod.user_id == req.user_id,
            BankDetail.account_number_enc == req.account_number,
        )
        .first()
    )

    if existing_bank:
        raise HTTPException(
            status_code=409, detail="Bank account already exists for this user"
        )

    if req.make_primary:
        _clear_primary(db, req.user_id)

    pm = UserPaymentMethod(
        id=_gen_id(),
        user_id=req.user_id,
        type=PaymentMethodType.BANK,
        is_primary=req.make_primary,
        nickname=req.nickname,
    )

    db.add(pm)
    db.flush()

    db.add(
        BankDetail(
            id=_gen_id(),
            payment_method_id=pm.id,
            account_holder_name=req.account_holder_name,
            account_number_enc=req.account_number,
            masked_account=_mask_account(req.account_number),
            ifsc_code=req.ifsc_code,
            bank_name=req.bank_name.value,
            account_type=req.account_type,
        )
    )

    db.commit()
    db.refresh(pm)
    return _serialize(pm)


def get_all_methods(db: Session, user_id: str) -> dict:
    methods = (
        db.query(UserPaymentMethod)
        .filter(UserPaymentMethod.user_id == user_id)
        .order_by(UserPaymentMethod.created_at.desc())
        .all()
    )
    cards, upis, banks = [], [], []
    for pm in methods:
        s = _serialize(pm)
        if pm.type == PaymentMethodType.CARD:
            cards.append(s)
        elif pm.type == PaymentMethodType.UPI:
            upis.append(s)
        elif pm.type == PaymentMethodType.BANK:
            banks.append(s)
    return {"cards": cards, "upi": upis, "banks": banks, "total": len(methods)}


def get_method_by_id(db: Session, user_id: str, method_id: str):
    pm = (
        db.query(UserPaymentMethod)
        .filter(UserPaymentMethod.id == method_id, UserPaymentMethod.user_id == user_id)
        .first()
    )
    if not pm:
        raise HTTPException(status_code=404, detail="Payment method not found")
    return _serialize(pm)


def set_primary(db: Session, user_id: str, method_id: str) -> dict:
    pm = (
        db.query(UserPaymentMethod)
        .filter(UserPaymentMethod.id == method_id, UserPaymentMethod.user_id == user_id)
        .first()
    )
    if not pm:
        raise HTTPException(status_code=404, detail="Payment method not found")
    _clear_primary(db, user_id)
    pm.is_primary = True
    db.commit()
    return {"success": True, "primary_id": method_id}


def delete_method(db: Session, user_id: str, method_id: str):
    pm = (
        db.query(UserPaymentMethod)
        .filter(UserPaymentMethod.id == method_id, UserPaymentMethod.user_id == user_id)
        .first()
    )
    if not pm:
        raise HTTPException(status_code=404, detail="Payment method not found")
    db.delete(pm)
    db.commit()
    return {"success": True, "deleted_id": method_id}
