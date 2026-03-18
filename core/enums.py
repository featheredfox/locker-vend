# ========== USER & AUTHENTICATION =========================================

class UserLevel:
    OPERATOR = 10
    ADMIN = 20
    SUPER = 30

# ========== UI & NAVIGATION ===============================================

class PageID:
    LOGIN = 1
    DASHBOARD = 2
    TAKE = 3
    RESTOCK = 4
    TRANSACTION = 5
    DIR_ACTIONS = 6
    ADD_DIR = 7
    DELETE_DIR = 8
    UPDATE_DIR = 9
    CNT_OPS = 10
    ADD_CNT = 11
    DELETE_CNT = 12
    ASSIGN_CNT = 13
    UNASSIGN_CNT = 14

class DashboardAction:
    TAKE = 1
    RESTOCK = 2
    DIR_OPS = 3
    CNT_OPS = 4
    CONFIG = 5
    CHNG_PIN = 6
    LOGOUT = 7

class ConfirmChoice:
    YES = 1
    NO = 2

# ========== SYSTEM & INPUT ================================================

class InputError:
    TIMEOUT = 1
    MAX_LENGTH = 2
    INVALID = 3

class TimeoutAction:
    LOGOUT = 1
    RETRY = 2

class SortOrder:
    ASC = 1
    DESC = 2

# ========== HARDWARE ======================================================

class HardwareMessage:
    OPENING = 1
    CLOSING = 2
    OPEN = 3
    CLOSED = 4

class HardwareError:
    NOT_OPENED = 1
    NOT_CLOSED = 2

class HrdwrePins:
    O_LOCK = 0
    I_SENS = 1
    O_LED_G = 2
    O_LED_R = 3

# ========== BUSINESS ENTITIES: INVENTORY, CONTAINERS & TRANSACTIONS =======

class InvError:
    NO_DIR_ITEMS = 1
    NO_STOCK = 2

class ContainerContent:
    UNKNOWN = 1
    EMPTY = 2    # Changed from 'NONE' to 'EMPTY' for better readability
    PRESENT = 3

class TxType:    # Shortened from TransactionType
    TAKE = 1
    RESTOCK = 2

class TxStatus:
    NONE = 1
    IN_PROGRESS = 2
    AWAIT_CONFIRMATION = 3
    CONFIRMED = 4
    COMPLETE = 5
    FAILED = 6
    CANCELLED = 7

class TxError:
    UNLOCK_FAILED = 1
    CONTAINER_NOT_CLOSED = 2
    USER_NOT_CONFIRMED = 3

class CntAction:
    ADD = 1
    DELETE = 2
    ASSIGN = 3
    UNASSIGN = 4

class CntMessage:
    ADDED = 1
    DELETED = 2
    UPDATED = 3
    ASSIGNED = 4
    UNASSIGNED = 5

class CntError:
    NOT_EMPTY = 1
    CONTENT_UNKNOWN = 2
    ALREADY_ASSIGNED = 3
    NOT_FOUND = 4

class CntField:
    LOCK_OUTPUT = 1
    SENS_INPUT = 2
    G_LED_OUTPUT = 3
    R_LED_OUTPUT = 4

class CntAssignStat:
    ASSIGNED = 1
    UNASSIGNED = 2

# ========== BUSINESS ENTITIES: DIRECTORY ==================================

class DirAction:
    ADD = 1
    DELETE = 2
    UPDATE = 3

class DirMessage:
    ADDED = 1
    DELETED = 2
    UPDATED = 3
    INVENTORY_ERROR = 4

class DirField:  # Replaces DirectoryOp.Add to clearly indicate it represents data fields
    NONE = 0
    PART_NO = 1
    MANUFACTURER = 2
    DESCRIPTION = 3