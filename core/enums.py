
# ========== USER AUTHENTIFICATION =========================================

class UserLevel:
    OPERATOR = 10
    ADMIN = 20
    SUPER = 30

# ========== USER INTERFACE ================================================

class UI:

    class UIPage:
        LOGIN = 1
        DASHBOARD = 2

    class DashboardActions:
        TAKE = 1
        RESTOCK = 2
        DIR_OPS = 3
        MOD_OPS = 4
        CONFIG = 5
        CHNG_PIN = 6
        LOGOUT = 7




class SystemMessage:

    class Input:
        TIMEOUT = 1
        MAX_LENGTH = 2
        INVALID = 3

        class TimeoutAction:
            LOGOUT = 1
            RETRY = 2


