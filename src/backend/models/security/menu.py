# src/backend/models/security/menu.py
from sqlalchemy import Column, String, Date, CHAR, Integer, text
from src.backend.utils.database import Base
from src.backend.utils.timezone import today_local

class Menu(Base):
    __tablename__ = "menus"

    menu_id            = Column(String(2), primary_key=True)
    menu_name          = Column(String(50), nullable=True)
    parent_id          = Column(String(2), nullable=True)                   # '0' or NULL = root
    is_parents         = Column(CHAR(1), nullable=False, server_default=text("'N'"))
    url                = Column(String(255), nullable=True)
    menu_order         = Column(Integer, nullable=True)
    font_awesome_icon  = Column(String(50), nullable=True)
    f_awesome_icon_css = Column(String(100), nullable=True)
    active_flag        = Column(CHAR(1), nullable=False, server_default=text("'Y'"))
    status             = Column(String(20), nullable=True, server_default=text("'active'"))
    created_by  = Column(String(20), nullable=True)
    created_dt   = Column(Date, default=today_local, nullable=False)
    updated_by  = Column(String(20), nullable=True)
    updated_dt   = Column(Date, default=today_local, nullable=False)