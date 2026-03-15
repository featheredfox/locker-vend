
from typing import Optional, List, Tuple
from core.enums import UserLevel, UI, SystemMessage, Transaction



def get_input_error_action(err_code: int, timeout_action: int = None) -> Tuple[Optional[str], Optional[str]]:
    
    obj_name, method_name = None, None

    match err_code:
        case SystemMessage.Input.TIMEOUT:
            match timeout_action:
                case SystemMessage.Input.TimeoutAction.LOGOUT: obj_name, method_name = 'auth', 'logout'
                case SystemMessage.Input.TimeoutAction.RETRY: method_name = '_wait_for_enter'
        case SystemMessage.Input.MAX_LENGTH | SystemMessage.Input.INVALID: method_name = '_wait_for_enter'
    return obj_name, method_name

def get_allowed_dashboard_actions(user_level: int) -> List[int]:
    allowed_actions = []
    allowed_actions.append(UI.DashboardActions.TAKE)
    allowed_actions.extend([UI.DashboardActions.RESTOCK, UI.DashboardActions.DIR_OPS, UI.DashboardActions.MOD_OPS]) if user_level >= UserLevel.ADMIN else None
    allowed_actions.extend([UI.DashboardActions.CONFIG]) if user_level >= UserLevel.SUPER else None
    allowed_actions.extend([UI.DashboardActions.CHNG_PIN, UI.DashboardActions.LOGOUT])
    return allowed_actions

def get_dashboard_action(selection: int) -> Tuple[Optional[str], Optional[str]]:

    obj_name, method_name = None, None

    match selection:
        case UI.DashboardActions.TAKE: method_name = 'take_screen'
        case UI.DashboardActions.RESTOCK: method_name = 'restock_screen'
        case UI.DashboardActions.DIR_OPS: method_name = 'dir_ops_screen'
        case UI.DashboardActions.MOD_OPS: method_name = 'mod_ops_screen'
        case UI.DashboardActions.CONFIG: method_name = 'config_screen'
        case UI.DashboardActions.CHNG_PIN: method_name = 'chng_pin_screen'
        case UI.DashboardActions.LOGOUT: obj_name, method_name = 'auth', 'logout'
    return obj_name, method_name

def get_transaction_action(transaction_status: int) -> Tuple[Optional[str], Optional[str]]:

    obj_name, method_name = None, None

    match transaction_status:
        case Transaction.Status.NONE: obj_name, method_name = 'transaction', 'process'
        case Transaction.Status.CONFIRMED: obj_name, method_name = 'transaction', 'finalize'
        case Transaction.Status.CANCELLED: obj_name, method_name = 'transaction', 'cancelled'
        case Transaction.Status.FAILED: obj_name, method_name = 'transaction', 'failed'
    return obj_name, method_name

class ActionDispatcher:
    OBJECT = 0
    METHOD = 1

    @staticmethod
    def execute(app_context, action: tuple, **kwargs):
        """Dynamically executes a method based on the rulebook's routing instructions."""
        obj_name = action[ActionDispatcher.OBJECT]
        method_name = action[ActionDispatcher.METHOD]
        
        if not method_name:
            return False, None

        if obj_name is None:
            method_to_call = getattr(app_context, method_name)
        else:
            target_obj = getattr(app_context, obj_name)
            method_to_call = getattr(target_obj, method_name)
            
        return method_to_call(**kwargs)
