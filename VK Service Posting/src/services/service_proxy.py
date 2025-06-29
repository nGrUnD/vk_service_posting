from src.schemas.proxy import ProxyAdd
from src.utils.database_manager import DataBaseManager


def parse_proxies_from_text(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]

class ProxyService:
    def __init__(self, database: DataBaseManager, user_id):
        self.database = database
        self.user_id = user_id

    async def add_proxies(self, proxys: str):
        proxies = parse_proxies_from_text(proxys)

        for proxy in proxies:
            new_proxy = ProxyAdd(
                user_id=self.user_id,
                http=proxy,
            )
            db_proxy = await self.database.proxy.add(new_proxy)
        await self.database.commit()

        return proxies