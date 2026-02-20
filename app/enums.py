from enum import Enum

class OrderStatus(str, Enum):
    NEW = "NEW"
    NEED_INFO = "NEED_INFO"
    PRICE_SENT = "PRICE_SENT"
    CONFIRMED = "CONFIRMED"
    PAYMENT_REPORTED = "PAYMENT_REPORTED"
    IN_PROGRESS = "IN_PROGRESS"
    READY = "READY"
    DONE = "DONE"
    CANCELED = "CANCELED"

class FileRole(str, Enum):
    DESIGN = "DESIGN"
    PAYMENT_PROOF = "PAYMENT_PROOF"

class SupportStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"

class ActorRole(str, Enum):
    CLIENT = "CLIENT"
    ADMIN = "ADMIN"