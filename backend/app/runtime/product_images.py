"""Optional public image links. Images are display data, never product evidence."""
import ipaddress
from urllib.parse import urlparse

def image_url(value):
    if not isinstance(value,str) or len(value)>4000:return ""
    try:
        p=urlparse(value)
        if p.scheme!="https" or not p.hostname or p.username or p.password or p.port not in (None,443):return ""
        if "." not in p.hostname or p.hostname.endswith((".local",".localhost",".test")):return ""
        try:ipaddress.ip_address(p.hostname)
        except ValueError:return value
    except ValueError:pass
    return ""

def select_image(variant,product):
    for item in [*variant.get("media",[]),*product.get("media",[])]:
        if isinstance(item,dict) and item.get("type")=="image":
            url=image_url(item.get("url"))
            if url:return url,str(item.get("alt_text") or product.get("title") or "Product image")[:500]
    return "",""
