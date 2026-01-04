import panel as pn
from frontend.auth_view import auth_check

pn.extension()

def admin_dashboard(token: str):
    user = auth_check(token)
    if not user or user['role'] != 'admin':
        return pn.pane.Markdown("Access Denied", style={'color':'red'})
    return pn.Column("# Admin Dashboard", "Manage Users, Reports and AI Agents")