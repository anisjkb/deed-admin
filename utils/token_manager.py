from src.backend.utils.security import decode_access_token
def get_current_user(token: str):
    payload = decode_access_token(token)
    if payload:
        return {"username": payload.get("sub"), "role": payload.get("role")}
    return None
