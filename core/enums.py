
# ========== USER AUTHENTIFICATION =========================================

class UserLevel:
    OPERATOR = 10
    ADMIN = 20
    SUPER = 30

# ========== USER INTERFACE ================================================

# ===== PAGE & ACTION POINTER CONSTANTS ====================================

class UI:

    class UIPage:
        LOGIN = 1
        DASHBOARD = 2
        TAKE = 3
        RESTOCK = 4
        TRANSACTION = 5

    class DashboardActions:
        TAKE = 1
        RESTOCK = 2
        DIR_OPS = 3
        MOD_OPS = 4
        CONFIG = 5
        CHNG_PIN = 6
        LOGOUT = 7

# ===== MESSAGE POINTER CONSTANTS ==========================================

class SystemMessage:

    class Input:
        TIMEOUT = 1
        MAX_LENGTH = 2
        INVALID = 3

        class TimeoutAction:
            LOGOUT = 1
            RETRY = 2

# ========== VEND CONTAINER CONSTANTS =======================================

class Container:

    class Status:
        
        class Hardware:

            class Message:
                OPENING = 1
                CLOSING = 2
                OPEN = 3
                CLOSED = 4

            class Error:
                NOT_OPENED = 1
                NOT_CLOSED = 2

        class Content:
            UNKNOWN = 1
            NONE = 2
            PRESENT = 3

class Transaction:

    class Type:
        TAKE = 1
        RESTOCK = 2

    class Status:
        NONE = 1
        IN_PROGRESS = 2
        AWAIT_CONFIRMATION = 3
        CONFIRMED = 4
        COMPLETE = 5
        FAILED = 6
        CANCELLED = 7

    class Error:
        UNLOCK_FAILED = 1
        CONTAINER_NOT_CLOSED = 2
        TRANSACTION_NOT_CONFIRMED = 3

class Misc:

    class SortOrder:
        ASC = 1
        DESC = 2

    class Confirm:
        YES = 1
        NO = 2

