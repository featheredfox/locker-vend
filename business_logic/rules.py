from typing import Optional, List, Tuple
from core.enums import UserLevel, PageID, DashboardAction, InputError, TimeoutAction, TxStatus, DirAction, CntAction, DirField, CntField
from presentation.views import InputPrompt

def get_input_error_action(err_code: int, timeout_action: int = None) -> Tuple[str, str, Optional[str]]:
    if err_code == InputError.TIMEOUT and timeout_action == TimeoutAction.LOGOUT:
        return ('service', 'auth', 'logout')
    return ('method', '_wait_for_enter', None)

def get_allowed_dashboard_actions(user_level: int) -> List[int]:
    allowed_actions = [DashboardAction.TAKE]
    if user_level >= UserLevel.ADMIN:
        allowed_actions.extend([DashboardAction.RESTOCK, DashboardAction.DIR_OPS, DashboardAction.CNT_OPS])
    if user_level >= UserLevel.SUPER:
        allowed_actions.extend([DashboardAction.CONFIG])
    allowed_actions.extend([DashboardAction.CHNG_PIN, DashboardAction.LOGOUT])
    return allowed_actions

def get_dashboard_action(selection: int) -> Tuple:
    match selection:
        case DashboardAction.TAKE: return ('screen', 'TakeScreen')
        case DashboardAction.RESTOCK: return ('screen', 'RestockScreen')
        case DashboardAction.DIR_OPS: return ('screen', 'DirectoryOpsScreen')
        case DashboardAction.CNT_OPS: return ('screen', 'ContainerOpsScreen')
        case DashboardAction.CONFIG: return ('screen', 'ConfigScreen')
        case DashboardAction.CHNG_PIN: return ('screen', 'ChangePinScreen')
        case DashboardAction.LOGOUT: return ('service', 'auth', 'logout')
    return ('screen', 'DashboardScreen')

def get_transaction_action(tx_status: int) -> Tuple:
    match tx_status:
        case TxStatus.NONE: return ('service', 'transaction', 'process')
        case TxStatus.CONFIRMED: return ('service', 'transaction', 'finalize')
        case TxStatus.CANCELLED: return ('service', 'transaction', 'cancelled')
        case TxStatus.FAILED: return ('service', 'transaction', 'failed')
    return ('screen', 'DashboardScreen')

def get_directory_action(selection: int) -> Tuple:
    match selection:
        case DirAction.ADD: return ('screen', 'DirAddScreen')
        case DirAction.DELETE: return ('screen', 'DirDeleteScreen')
        case DirAction.UPDATE: return ('screen', 'DirUpdateScreen')
    return ('screen', 'DirectoryOpsScreen')

def get_cnt_action(selection: int) -> Tuple:
    match selection:
        case CntAction.ADD: return ('screen', 'CntAddScreen')
        case CntAction.DELETE: return ('screen', 'CntDeleteScreen')
        # case CntAction.UPDATE: return ('screen', 'CntUpdateScreen')
        case CntAction.ASSIGN: return ('screen', 'CntAssignScreen')
        case CntAction.UNASSIGN: return ('screen', 'CntUnassignScreen')
    return ('screen', 'ContainerOpsScreen')

def get_input_fields(page: int) -> List:
    match page:
        case PageID.ADD_DIR | PageID.UPDATE_DIR: 
            return [
                {'prompt': InputPrompt.directory_add_string(DirField.PART_NO), 'input_type': str, 'max_len': 15, 'timeout': 60}, 
                {'prompt': InputPrompt.directory_add_string(DirField.MANUFACTURER), 'input_type': str, 'max_len': 15, 'timeout': 60}, 
                {'prompt': InputPrompt.directory_add_string(DirField.DESCRIPTION), 'input_type': str, 'max_len': 15, 'timeout': 60}
            ]
        case PageID.ADD_CNT:
            return [
                {'prompt': InputPrompt.container_add_string(CntField.LOCK_OUTPUT), 'input_type': int, 'max_len': 4, 'timeout': 60},
                {'prompt': InputPrompt.container_add_string(CntField.SENS_INPUT), 'input_type': int, 'max_len': 4, 'timeout': 60},
                {'prompt': InputPrompt.container_add_string(CntField.G_LED_OUTPUT), 'input_type': int, 'max_len': 4, 'timeout': 60},
                {'prompt': InputPrompt.container_add_string(CntField.R_LED_OUTPUT), 'input_type': int, 'max_len': 4, 'timeout': 60}
            ]



class ActionDispatcher:
    @staticmethod
    def execute(app_context, action: tuple, **kwargs):
        """Dynamically routes execution based on the 3-part Rule Tuple."""
        action_type = action[0]
        
        if action_type == 'screen':
            screen_name = action[1]
            app_context.set_screen(screen_name, **kwargs)
            return True
            
        elif action_type == 'service':
            obj_name = action[1]
            method_name = action[2]
            target_obj = getattr(app_context, obj_name)
            method_to_call = getattr(target_obj, method_name)
            return method_to_call(**kwargs)
            
        elif action_type == 'method':
            method_name = action[1]
            # Calls method natively on the current active screen
            target = app_context.current_screen if hasattr(app_context, 'current_screen') else app_context
            method_to_call = getattr(target, method_name, None)
            if method_to_call:
                return method_to_call(**kwargs)
                
        return False