from utils.token_manager import get_current_user
import panel as pn

def auth_check(token: str):
    user = get_current_user(token)
    if not user:
        return pn.pane.Markdown("Unauthorized", style={'color':'red'})
    return user