import re
import uuid
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, field_validator, model_validator


class PaymentMethodType(str, Enum):
    CARD = "card"
    UPI = "upi"
    BANK = "bank"


class CardNetwork(str, Enum):
    VISA = "visa"
    MASTERCARD = "mastercard"
    RUPAY = "rupay"
    AMEX = "amex"
    DINERS = "diners"
    UNKNOWN = "unknown"


class IndianBank(str, Enum):
    SBI = "State Bank of India"
    HDFC = "HDFC Bank"
    ICICI = "ICICI Bank"
    AXIS = "Axis Bank"
    KOTAK = "Kotak Mahindra Bank"
    PNB = "Punjab National Bank"
    BOB = "Bank of Baroda"
    CANARA = "Canara Bank"
    UNION = "Union Bank of India"
    IDBI = "IDBI Bank"
    YES = "Yes Bank"
    INDUSIND = "IndusInd Bank"
    FEDERAL = "Federal Bank"
    IOB = "Indian Overseas Bank"
    BOI = "Bank of India"
    OTHER = "Other"


class AccountType(str, Enum):
    SAVINGS = "savings"
    CURRENT = "current"


class AddCardRequest(BaseModel):
    user_id: str
    card_number: str  # Will be stored as last4 only
    card_holder_name: str
    expiry_month: int  # 1-12
    expiry_year: int  # e.g. 2027
    cvv: str  # Validated but never stored
    make_primary: bool = False
    nickname: Optional[str] = None  # e.g. "My HDFC Card"

    @field_validator("card_number")
    @classmethod
    def validate_card_number(cls, v):
        digits = re.sub(r"\s|-", "", v)
        if not digits.isdigit():
            raise ValueError("Card number must contain only digits")
        if len(digits) < 13 or len(digits) > 19:
            raise ValueError("Card number must be 13–19 digits")
        # Luhn check
        total = 0
        reverse = digits[::-1]
        for i, d in enumerate(reverse):
            n = int(d)
            if i % 2 == 1:
                n *= 2
                if n > 9:
                    n -= 9
            total += n
        if total % 10 != 0:
            raise ValueError("Invalid card number (Luhn check failed)")
        return digits

    @field_validator("expiry_month")
    @classmethod
    def validate_month(cls, v):
        if not 1 <= v <= 12:
            raise ValueError("Expiry month must be 1–12")
        return v

    @field_validator("expiry_year")
    @classmethod
    def validate_year(cls, v):
        if v < 2024 or v > 2040:
            raise ValueError("Expiry year out of range")
        return v

    @field_validator("cvv")
    @classmethod
    def validate_cvv(cls, v):
        if not re.match(r"^\d{3,4}$", v):
            raise ValueError("CVV must be 3 or 4 digits")
        return v

    @field_validator("card_holder_name")
    @classmethod
    def validate_name(cls, v):
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Card holder name too short")
        return v.upper()


class CardResponse(BaseModel):
    id: uuid.UUID
    type: Literal["card"] = "card"
    last4: str
    card_holder_name: str
    expiry_month: int
    expiry_year: str
    network: CardNetwork
    nickname: Optional[str]
    is_primary: bool
    created_at: str


class AddUPIRequest(BaseModel):
    user_id: str
    upi_id: str
    make_primary: bool = False
    nickname: Optional[str] = None

    @field_validator("upi_id")
    @classmethod
    def validate_upi(cls, v):
        v = v.strip().lower()
        if not re.match(r"^[\w.\-+]+@[a-z]+$", v):
            raise ValueError(
                "Invalid UPI ID format. Example: name@okaxis or 9876543210@paytm"
            )
        return v


KNOWN_UPI_PSPS = {
    "okaxis": "Axis Bank",
    "okhdfcbank": "HDFC Bank",
    "okicici": "ICICI Bank",
    "oksbi": "State Bank of India",
    "ybl": "Yes Bank / PhonePe",
    "ibl": "ICICI Bank / PhonePe",
    "axl": "Axis Bank / PhonePe",
    "paytm": "Paytm",
    "upi": "BHIM UPI",
    "apl": "Amazon Pay",
    "jupiteraxis": "Jupiter / Axis",
    "fbl": "Federal Bank",
    "kotak": "Kotak Mahindra",
    "icici": "ICICI Bank",
    "sbi": "State Bank of India",
    "hdfc": "HDFC Bank",
}


class UPIResponse(BaseModel):
    id: str
    type: Literal["upi"] = "upi"
    upi_id: str
    psp: str
    nickname: Optional[str]
    is_primary: bool
    created_at: str


class AddBankRequest(BaseModel):
    user_id: str
    account_holder_name: str
    account_number: str
    confirm_account_number: str
    ifsc_code: str
    bank_name: IndianBank = IndianBank.OTHER
    account_type: AccountType = AccountType.SAVINGS
    make_primary: bool = False
    nickname: Optional[str] = None

    @field_validator("account_number")
    @classmethod
    def validate_account_number(cls, v):
        v = v.strip()
        if not re.match(r"^\d{9,18}$", v):
            raise ValueError("Account number must be 9–18 digits")
        return v

    @field_validator("ifsc_code")
    @classmethod
    def validate_ifsc(cls, v):
        v = v.strip().upper()
        # IFSC: 4 letters (bank code) + 0 + 6 alphanumeric
        if not re.match(r"^[A-Z]{4}0[A-Z0-9]{6}$", v):
            raise ValueError("Invalid IFSC code. Format: ABCD0123456")
        return v

    @field_validator("account_holder_name")
    @classmethod
    def validate_holder(cls, v):
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Account holder name too short")
        return v.upper()

    @model_validator(mode="after")
    def accounts_match(self):
        if self.account_number != self.confirm_account_number:
            raise ValueError("Account number and confirmation do not match")
        return self

    @model_validator(mode="after")
    def auto_detect_bank(self):
        """Auto-detect bank from IFSC if bank_name is OTHER"""
        if self.bank_name == IndianBank.OTHER and self.ifsc_code:
            prefix = self.ifsc_code[:4].upper()
            bank_map = {
                "SBIN": IndianBank.SBI,
                "HDFC": IndianBank.HDFC,
                "ICIC": IndianBank.ICICI,
                "UTIB": IndianBank.AXIS,
                "KKBK": IndianBank.KOTAK,
                "PUNB": IndianBank.PNB,
                "BARB": IndianBank.BOB,
                "CNRB": IndianBank.CANARA,
                "UBIN": IndianBank.UNION,
                "IBKL": IndianBank.IDBI,
                "YESB": IndianBank.YES,
                "INDB": IndianBank.INDUSIND,
                "FDRL": IndianBank.FEDERAL,
                "IOBA": IndianBank.IOB,
                "BKID": IndianBank.BOI,
            }
            self.bank_name = bank_map.get(prefix, IndianBank.OTHER)
        return self


class BankResponse(BaseModel):
    id: str
    type: Literal["bank"] = "bank"
    account_holder_name: str
    masked_account: str
    ifsc_code: str
    bank_name: str
    account_type: AccountType
    nickname: Optional[str]
    is_primary: bool
    created_at: str


class SetPrimaryRequest(BaseModel):
    user_id: str
    method_id: str


class DeleteMethodRequest(BaseModel):
    user_id: str
    method_id: str
