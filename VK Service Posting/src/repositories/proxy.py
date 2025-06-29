from src.models.proxy import ProxyOrm
from src.schemas.proxy import Proxy
from src.repositories.base import BaseRepository


class ProxyRepository(BaseRepository):
    model = ProxyOrm
    schema = Proxy