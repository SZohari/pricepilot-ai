"""Conservative, configured JSON-LD offer collector. Never guesses a SKU or shipping."""
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from html.parser import HTMLParser
import http.client
import ipaddress
import json
from pathlib import Path
import socket
import ssl
from threading import Lock
import time
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser
from typing import Annotated

from pydantic import Field, HttpUrl, UrlConstraints, field_validator
from src.domain.models import Contract, Cost, Identifier, Observation, validate_gtin

USER_AGENT = "PricePilotMVP/1.0"
MAX_BYTES = 2_000_000


class Source(Contract):
    source_id: Identifier
    product_id: Identifier
    seller: str = Field(min_length=1, max_length=120)
    url: Annotated[HttpUrl, UrlConstraints(allowed_schemes=["https"])]
    expected_gtin: str
    # Explicit merchant-configured delivery assumption; never silently defaults to free.
    shipping_gross: Cost
    shipping_note: str = Field(min_length=1, max_length=160)

    @field_validator("expected_gtin")
    @classmethod
    def valid_gtin(cls, value):
        return validate_gtin(value)

    @field_validator("url")
    @classmethod
    def public_url(cls, value):
        if value.username or value.password or value.port not in (None,443) or value.fragment:
            raise ValueError("Source URL must use HTTPS port 443 without credentials or fragment")
        return value


class CollectionError(ValueError):
    pass


def load_sources(path):
    if not path:
        return []
    values=json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(values,list) or len(values)>24:
        raise ValueError("Configure at most 24 explicit source URLs per MVP process")
    sources=[Source.model_validate(v) for v in values]
    if len({s.source_id for s in sources})!=len(sources):
        raise ValueError("Source IDs must be unique")
    identities={}
    sellers=set()
    for source in sources:
        old=identities.setdefault(source.product_id,source.expected_gtin.lstrip("0"))
        if old!=source.expected_gtin.lstrip("0"):
            raise ValueError("Every source for a product must refer to the same GTIN/variant")
        key=(source.product_id,source.seller.casefold())
        if key in sellers:
            raise ValueError("Only one configured offer per product and seller")
        sellers.add(key)
    return sources


def public_addresses(host):
    addresses=list(dict.fromkeys(item[4][0] for item in socket.getaddrinfo(host,443,type=socket.SOCK_STREAM)))
    if not addresses or any(not ipaddress.ip_address(ip).is_global for ip in addresses):
        raise CollectionError("Private, local or reserved network destinations are not allowed")
    return addresses


class PinnedHTTPSConnection(http.client.HTTPSConnection):
    """Connect to the validated IP while preserving certificate validation and SNI."""
    def __init__(self,host,address):
        super().__init__(host,timeout=12,context=ssl.create_default_context())
        self.address=address

    def connect(self):
        raw=socket.create_connection((self.address,443),self.timeout)
        try:
            self.sock=self._context.wrap_socket(raw,server_hostname=self.host)
        except Exception:
            raw.close()
            raise


def fetch_public(url):
    parsed=urlsplit(url)
    if parsed.scheme!="https" or not parsed.hostname or parsed.username or parsed.password or parsed.port not in (None,443):
        raise CollectionError("Only public HTTPS URLs are supported")
    connection=PinnedHTTPSConnection(parsed.hostname,public_addresses(parsed.hostname)[0])
    try:
        path=parsed.path or "/"
        if parsed.query: path+="?"+parsed.query
        connection.request("GET",path,headers={"User-Agent":USER_AGENT,"Accept":"text/html,text/plain","Accept-Encoding":"identity"})
        response=connection.getresponse()
        # Never follow an unchecked redirect or attempt CAPTCHA/anti-bot bypass.
        if response.status!=200:
            raise CollectionError(f"HTTP {response.status}; source was not imported (redirects require updating the configured URL)")
        body=response.read(MAX_BYTES+1)
        if len(body)>MAX_BYTES: raise CollectionError("Source exceeds the 2 MB response limit")
        return body.decode("utf-8",errors="replace")
    finally:
        connection.close()


class JsonLdParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.inside=False; self.parts=[]; self.documents=[]

    def handle_starttag(self,tag,attrs):
        if tag.lower()=="script" and dict(attrs).get("type","").lower()=="application/ld+json":
            self.inside=True; self.parts=[]

    def handle_data(self,data):
        if self.inside: self.parts.append(data)

    def handle_endtag(self,tag):
        if tag.lower()=="script" and self.inside:
            try: self.documents.append(json.loads("".join(self.parts)))
            except (ValueError,RecursionError): pass
            self.inside=False


def nodes(value):
    if isinstance(value,list):
        for child in value: yield from nodes(child)
    elif isinstance(value,dict):
        yield value
        for child in value.values():
            if isinstance(child,(dict,list)): yield from nodes(child)


def has_type(node,kind):
    types=node.get("@type",[])
    if isinstance(types,str): types=[types]
    return any(t.rsplit("/",1)[-1]==kind for t in types if isinstance(t,str))


def parse_offer(html,source,now=None):
    now=now or datetime.now(timezone.utc)
    parser=JsonLdParser();parser.feed(html)
    products=[n for n in nodes(parser.documents) if has_type(n,"Product") and
              any(str(n.get(k,"")).lstrip("0")==source.expected_gtin.lstrip("0") for k in ("gtin","gtin8","gtin12","gtin13","gtin14"))]
    if len(products)!=1: raise CollectionError("Exact GTIN match is missing or ambiguous; no model-name approximation was imported")
    offers=products[0].get("offers",[])
    if isinstance(offers,dict): offers=[offers]
    usable=[]
    for offer in offers:
        if not isinstance(offer,dict) or not has_type(offer,"Offer"): continue
        if offer.get("priceCurrency")!="EUR": continue
        if offer.get("itemCondition","").rsplit("/",1)[-1]!="NewCondition": continue
        availability=offer.get("availability","").rsplit("/",1)[-1]
        if availability not in ("InStock","OutOfStock","SoldOut","Discontinued"): continue
        if offer.get("priceValidUntil"):
            try:
                if date.fromisoformat(offer["priceValidUntil"][:10])<now.date(): continue
            except (ValueError,TypeError): continue
        try:
            price=Decimal(str(offer.get("price")))
            if not price.is_finite() or price<=0 or price!=price.quantize(Decimal(".01")): continue
        except (InvalidOperation,TypeError,ValueError): continue
        usable.append((price,availability=="InStock"))
    if len(usable)!=1:
        raise CollectionError("Need one unambiguous new-condition EUR offer with explicit price and availability; aggregate/range prices are not supported")
    price,available=usable[0]
    oid=sha256((source.source_id+now.isoformat()).encode()).hexdigest()[:32]
    return Observation(observation_id="LIVE-"+oid,product_id=source.product_id,seller=source.seller,
        price_gross=price,shipping_gross=source.shipping_gross,available=available,observed_on=now.date(),
        observed_at=now,source="JSON-LD; GTIN verified; delivery: "+source.shipping_note[:100],
        source_url=source.url,data_origin="live")


class Collector:
    def __init__(self,sources,fetch=fetch_public):
        self.sources=sources;self.fetch=fetch;self.cache={};self.lock=Lock();self.robots={};self.last_request={}

    def collect(self,source):
        # Across all visitor sessions: no more than one request cycle/source/5 min.
        with self.lock:
            # A caller-chosen ID alone must not alias another session's URL or SKU.
            cache_key=sha256(source.model_dump_json().encode()).hexdigest()
            cached=self.cache.get(cache_key)
            if cached and time.monotonic()-cached[0]<300:
                return {**cached[1],"cached":True}
            try:
                parsed=urlsplit(str(source.url))
                robot_url=f"https://{parsed.netloc}/robots.txt"
                cached_robots=self.robots.get(parsed.netloc)
                if cached_robots and time.monotonic()-cached_robots[0]<300:
                    robots=cached_robots[1]
                else:
                    robots=RobotFileParser(robot_url)
                    robots.parse(self.fetch(robot_url).splitlines())
                    self.last_request[parsed.netloc]=time.monotonic()
                    self.robots[parsed.netloc]=(time.monotonic(),robots)
                if not robots.can_fetch(USER_AGENT,str(source.url)):
                    raise CollectionError("Collection is disallowed by this site's robots policy")
                rate=robots.request_rate(USER_AGENT)
                delay=max(1,robots.crawl_delay(USER_AGENT) or 0,rate.seconds/rate.requests if rate and rate.requests else 0)
                if delay>30:
                    raise CollectionError("Site requires a longer crawl interval; configure a dedicated connector")
                wait=delay-(time.monotonic()-self.last_request.get(parsed.netloc,0))
                if wait>0: time.sleep(wait)
                try:
                    html=self.fetch(str(source.url))
                finally:
                    self.last_request[parsed.netloc]=time.monotonic()
                observation=parse_offer(html,source)
                result={"status":"collected","source_id":source.source_id,"observation":observation.model_dump(mode="json"),"cached":False}
            except (ValueError,OSError,http.client.HTTPException,RecursionError) as exc:
                result={"status":"failed","source_id":source.source_id,"message":str(exc)[:250],"cached":False}
            # Bound memory even when the local owner cycles through many sessions.
            if len(self.cache)>=1536:
                self.cache={k:v for k,v in self.cache.items() if time.monotonic()-v[0]<300}
                if len(self.cache)>=1536: self.cache.pop(next(iter(self.cache)))
            self.cache[cache_key]=(time.monotonic(),result)
            return result
