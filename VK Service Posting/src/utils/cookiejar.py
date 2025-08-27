import requests
from http.cookiejar import Cookie
from typing import List, Dict, Any, Optional

def cookiejar_to_list(jar: requests.cookies.RequestsCookieJar) -> List[Dict[str, Any]]:
    result = []
    for c in jar:
        result.append({
            "name": c.name,
            "value": c.value,
            "domain": c.domain,
            "path": c.path,
            "expires": c.expires,
            "secure": c.secure,
            # HttpOnly и пр. флаги requests кладёт в c._rest
            "rest": getattr(c, "_rest", None),
        })
    return result

def list_to_cookiejar(cookies: List[Dict[str, Any]]) -> requests.cookies.RequestsCookieJar:
    jar = requests.cookies.RequestsCookieJar()
    for item in cookies:
        cookie = requests.cookies.create_cookie(
            name=item["name"],
            value=item["value"],
            domain=item.get("domain"),
            path=item.get("path", "/"),
            expires=item.get("expires"),
            secure=item.get("secure") or False,
            rest=item.get("rest") or {},
        )
        jar.set_cookie(cookie)
    return jar