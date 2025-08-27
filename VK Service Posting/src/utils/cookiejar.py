import requests
from http.cookiejar import Cookie
from typing import List, Dict, Any, Optional

def cookiejar_to_list(jar: requests.cookies.RequestsCookieJar) -> List[Dict[str, Any]]:
    cookies: List[Dict[str, Any]] = []
    for c in jar:
        # В requests это экземпляры http.cookiejar.Cookie
        rest = getattr(c, "_rest", None)
        cookies.append({
            "comment": c.comment,
            "comment_url": getattr(c, "comment_url", None),
            "discard": bool(c.discard),
            "domain": c.domain,
            "domain_initial_dot": bool(c.domain_initial_dot),
            "domain_specified": bool(c.domain_specified),
            "expires": c.expires,  # Unix timestamp или None
            "name": c.name,
            "path": c.path,
            "path_specified": bool(c.path_specified),
            "port": c.port,  # может быть None
            "port_specified": bool(c.port_specified),
            "rest": rest if isinstance(rest, dict) else {},
            "rfc2109": bool(getattr(c, "rfc2109", False)),
            "secure": bool(c.secure),
            "value": c.value,
            "version": int(getattr(c, "version", 0) or 0),
        })
    return cookies


def _make_cookie(d: Dict[str, Any]) -> Cookie:
    return Cookie(
        version=int(d.get("version", 0) or 0),
        name=d["name"],
        value=d["value"],
        port=d.get("port"),
        port_specified=bool(d.get("port_specified", False)),
        domain=d["domain"],
        domain_specified=bool(d.get("domain_specified", True)),
        domain_initial_dot=bool(d.get("domain_initial_dot", d.get("domain","").startswith("."))),
        path=d.get("path", "/"),
        path_specified=bool(d.get("path_specified", True)),
        secure=bool(d.get("secure", False)),
        expires=d.get("expires"),  # int|None
        discard=bool(d.get("discard", False)),
        comment=d.get("comment"),
        comment_url=d.get("comment_url"),
        rest=d.get("rest", {}),  # {"HttpOnly": None} и т.п.
        rfc2109=bool(d.get("rfc2109", False)),
    )

def list_to_cookiejar(cookies: List[Dict[str, Any]]) -> requests.cookies.RequestsCookieJar:
    jar = requests.cookies.RequestsCookieJar()
    for d in cookies:
        cookie = _make_cookie(d)
        jar.set_cookie(cookie)
    return jar