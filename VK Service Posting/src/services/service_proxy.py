import random

from src.models.proxy import ProxyOrm
from src.schemas.proxy import ProxyAdd
from src.schemas.vk_account import VKAccountUpdate
from src.services.live_log import livelogadd
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
        await livelogadd(
            self.database,
            self.user_id,
            "proxy",
            "Прокси добавлены",
            f"count={len(proxies)}",
        )

        return proxies

    async def remove_proxies(self, proxys: list[str]):
        """Удаляет прокси по списку http; перед удалением переназначает vk_account на другой прокси пользователя."""
        all_proxies = await self.database.proxy.get_all_filtered(user_id=self.user_id)
        to_delete = [p for p in all_proxies if p.http in proxys]
        ids_to_delete = [p.id for p in to_delete]
        other_proxies = [p for p in all_proxies if p.id not in ids_to_delete]
        new_proxy_id = random.choice(other_proxies).id if other_proxies else None

        for proxy_id in ids_to_delete:
            await self.database.vk_account.edit(
                VKAccountUpdate(proxy_id=new_proxy_id),
                proxy_id=proxy_id,
                user_id=self.user_id,
            )
        await self.database.proxy.delete_where(
            ProxyOrm.http.in_(proxys),
            ProxyOrm.user_id == self.user_id,
        )
        await self.database.commit()
        await livelogadd(
            self.database,
            self.user_id,
            "proxy",
            "Прокси удалены",
            f"count={len(ids_to_delete)}; reassigned_proxy_id={new_proxy_id or ''}",
        )

    async def delete_proxy_with_reassign(self, proxy_id: int) -> None:
        """Удаляет прокси: сначала переназначает все vk_account с этим proxy_id на другой случайный прокси пользователя."""
        all_proxies = await self.database.proxy.get_all_filtered(user_id=self.user_id)
        other_proxies = [p for p in all_proxies if p.id != proxy_id]
        new_proxy_id = random.choice(other_proxies).id if other_proxies else None
        affected_accounts = await self.database.vk_account.get_all_filtered(
            proxy_id=proxy_id,
            user_id=self.user_id,
        )

        await self.database.vk_account.edit(
            VKAccountUpdate(proxy_id=new_proxy_id),
            proxy_id=proxy_id,
            user_id=self.user_id,
        )
        await self.database.proxy.delete(id=proxy_id, user_id=self.user_id)
        await self.database.commit()
        await livelogadd(
            self.database,
            self.user_id,
            "proxy",
            "Прокси удалён",
            f"proxy_id={proxy_id}; reassigned_accounts={len(affected_accounts)}; reassigned_proxy_id={new_proxy_id or ''}",
        )