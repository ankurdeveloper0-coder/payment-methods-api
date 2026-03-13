import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def gen_uuid():
    return str(uuid.uuid4())


class PaymentMethodType(str, enum.Enum):
    CARD = "card"
    UPI = "upi"
    BANK = "bank"


class CardNetwork(str, enum.Enum):
    VISA = "visa"
    MASTERCARD = "mastercard"
    RUPAY = "rupay"
    AMEX = "amex"
    DINERS = "diners"
    UNKNOWN = "unknown"


class AccountType(str, enum.Enum):
    SAVINGS = "savings"
    CURRENT = "current"


class UserPaymentMethod(Base):
    """
    One row per payment method per user.
    type column decides which child table has the detail.
    """

    __tablename__ = "user_payment_methods"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    user_id = Column(String(36), nullable=False, index=True)
    type = Column(SAEnum(PaymentMethodType), nullable=False)
    is_primary = Column(Boolean, default=False, nullable=False)
    nickname = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # relationships (one-to-one)
    card = relationship(
        "CardDetail",
        back_populates="payment_method",
        uselist=False,
        cascade="all, delete-orphan",
    )
    upi = relationship(
        "UPIDetail",
        back_populates="payment_method",
        uselist=False,
        cascade="all, delete-orphan",
    )
    bank = relationship(
        "BankDetail",
        back_populates="payment_method",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<UserPaymentMethod id={self.id} user={self.user_id} type={self.type}>"


class CardDetail(Base):
    """
    Stores safe card info only.
    Full card number and CVV are NEVER stored.
    """

    __tablename__ = "card_details"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    payment_method_id = Column(
        String(36),
        ForeignKey("user_payment_methods.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    last4 = Column(String(4), nullable=False)
    card_holder_name = Column(String(100), nullable=False)
    expiry_month = Column(Integer, nullable=False)  # 1–12
    expiry_year = Column(Integer, nullable=False)  # e.g. 2027
    network = Column(SAEnum(CardNetwork), nullable=False, default=CardNetwork.UNKNOWN)

    # relationship back
    payment_method = relationship("UserPaymentMethod", back_populates="card")

    def __repr__(self):
        return f"<CardDetail last4={self.last4} network={self.network}>"


class UPIDetail(Base):
    """
    Stores UPI ID and resolved PSP name.
    e.g. rahul@okaxis → Axis Bank
    """

    __tablename__ = "upi_details"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    payment_method_id = Column(
        String(36),
        ForeignKey("user_payment_methods.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    upi_id = Column(String(100), nullable=False)
    psp = Column(String(100), nullable=True)

    payment_method = relationship("UserPaymentMethod", back_populates="upi")

    def __repr__(self):
        return f"<UPIDetail upi_id={self.upi_id}>"


class BankDetail(Base):
    """
    Stores bank account info.
    Full account number is stored encrypted (encrypt before insert in service layer).
    masked_account is pre-computed for display.
    """

    __tablename__ = "bank_details"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    payment_method_id = Column(
        String(36),
        ForeignKey("user_payment_methods.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    account_holder_name = Column(String(100), nullable=False)
    account_number_enc = Column(String(255), nullable=False)
    masked_account = Column(String(30), nullable=False)
    ifsc_code = Column(String(11), nullable=False)
    bank_name = Column(String(100), nullable=False)
    account_type = Column(
        SAEnum(AccountType), nullable=False, default=AccountType.SAVINGS
    )

    payment_method = relationship("UserPaymentMethod", back_populates="bank")

    def __repr__(self):
        return f"<BankDetail bank={self.bank_name} masked={self.masked_account}>"
