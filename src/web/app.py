"""Local web workspace: static UI, shared v1 services and isolated browser demos."""
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import date
import asyncio
import json
import hmac
import mimetypes
import os
from pathlib import Path
import secrets
from threading import RLock
import time

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from src.api.v1 import get_service, require_writer, router
from src.api.intelligence import router as intelligence_router
from src.api.advisor import router as advisor_router
from src.api.retail import router as retail_router
from src.application.service import PricingService, demo_service, load_demo
from src.infrastructure.repository import SQLiteRepository
from src.infrastructure.repository import ConflictError
from src.infrastructure.price_sources import Collector, Source, load_sources
from src.application.showcase import STORE, replay_offers
from src.domain.models import Contract, Observation, Product, Identifier
from src.domain.advisory import Consultation

STATIC = Path(__file__).parent / "static"
# Some Windows MIME registries label these as text/plain. Serve predictable
# types with nosniff enabled, regardless of the host's file associations.
mimetypes.add_type("font/woff2", ".woff2")
mimetypes.add_type("image/webp", ".webp")


@dataclass
class Session:
    service: PricingService
    token: str
    touched: float
    busy: bool = False
    sources: list = field(default_factory=list)


class LiveConnection(Contract):
    input: Consultation
    source: Source
    exact_variant_confirmed: bool


class ProductRefresh(Contract):
    product_id: Identifier


class Sessions:
    def __init__(self):
        self.items = {}
        self.lock = RLock()

    def get(self, key):
        with self.lock:
            now = time.monotonic()
            for old in list(self.items):
                if now - self.items[old].touched > 7200 and not self.items[old].busy:
                    self.items.pop(old).service.repository.close()
            if key not in self.items:
                if len(self.items) >= 64:
                    raise HTTPException(429, "Demo capacity reached. Please try again later.")
                key = secrets.token_urlsafe(32)
                self.items[key] = Session(demo_service(), secrets.token_urlsafe(32), now)
            session = self.items[key]
            session.touched = now
            return key, session

    def close(self):
        with self.lock:
            for session in self.items.values():
                session.service.repository.close()
            self.items.clear()


def create_app():
    sessions = Sessions()
    database = os.getenv("PRICEPILOT_DB_PATH")
    public_demo = os.getenv("PRICEPILOT_PUBLIC_DEMO") == "1"
    if database and public_demo:
        raise ValueError("Public hosting is demo-only; do not expose a persistent retailer database")
    persistent = PricingService(SQLiteRepository(database)) if database else None
    collector = Collector(load_sources(os.getenv("PRICEPILOT_SOURCES_PATH")))

    @asynccontextmanager
    async def lifespan(app):
        yield
        sessions.close()
        if persistent:
            persistent.repository.close()

    app = FastAPI(title="PricePilot workspace", version="1.7.0", lifespan=lifespan)
    hosts=["localhost", "127.0.0.1", "[::1]", "testserver"]
    hosts += [h.strip() for h in os.getenv("PRICEPILOT_ALLOWED_HOSTS", "").split(",") if h.strip()]
    if os.getenv("RENDER_EXTERNAL_HOSTNAME"): hosts.append(os.environ["RENDER_EXTERNAL_HOSTNAME"])
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=hosts)
    app.state.sessions = sessions
    app.state.collector = collector

    @app.middleware("http")
    async def workspace_session(request, call_next):
        # Public assets and health checks do not allocate demo databases.
        if request.url.path.startswith("/api/"):
            if request.method in ("POST", "PUT"):
                chunks=[];size=0
                async for chunk in request.stream():
                    size+=len(chunk)
                    if size>2_000_000:
                        return JSONResponse({"detail":"Request exceeds the 2 MB MVP limit"},status_code=413)
                    chunks.append(chunk)
                request._body=b"".join(chunks)
            try:
                key, session = sessions.get(request.cookies.get("pricepilot_session"))
            except HTTPException as exc:
                return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
            request.state.workspace = persistent or session.service
            request.state.session = session
        else:
            key = None
        response = await call_next(request)
        if key:
            response.set_cookie("pricepilot_session", key, httponly=True, secure=public_demo, samesite="strict", max_age=7200)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; connect-src 'self'; font-src 'self'; "
            "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        )
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    def service(request: Request):
        return request.state.workspace

    def writer(request: Request):
        if persistent:
            return require_writer(request.headers.get("X-API-Key"))
        token = request.headers.get("X-Workspace-Token", "")
        if not hmac.compare_digest(token, request.state.session.token):
            raise HTTPException(403, "Reload the workspace before saving.")
        entries,observations=request.state.workspace.repository.snapshot()
        if len(entries)>1000 or len(observations)>10000:
            raise HTTPException(429,"Demo capacity reached; export your data and reset the example")

    app.dependency_overrides[get_service] = service
    app.dependency_overrides[require_writer] = writer
    app.include_router(router)
    app.include_router(intelligence_router)
    app.include_router(advisor_router)
    app.include_router(retail_router)

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "PricePilot Web", "version": app.version}

    @app.get("/api/workspace")
    def workspace(request: Request):
        return {
            "mode": "local" if persistent else "demo",
            "as_of": str(date.today() if persistent else load_demo().as_of),
            "csrf_token": request.state.session.token,
            "can_write": not persistent,
            "store": STORE,
            "live_source_count": len(collector.sources) + len(request.state.session.sources),
            "public_demo": public_demo,
            "data_notice": "Real model references. Simulated prices, costs, inventory and sales.",
        }

    def event(payload):
        return "data: "+json.dumps(payload)+"\n\n"

    def reserve(request):
        if persistent:
            raise HTTPException(403,"Interactive replay/collection runs in isolated demo workspaces only")
        if request.state.session.busy:
            raise HTTPException(409,"A collection or replay is already running")
        request.state.session.busy=True

    def configured_sources(request):
        return collector.sources + request.state.session.sources

    @app.get("/api/sources")
    def sources(request: Request):
        configured = configured_sources(request)
        return {"configured":len(configured),"interval_seconds":300,
                "can_configure":not public_demo and not persistent,
                "sources":[s.model_dump(mode="json") for s in configured]}

    @app.post("/api/sources/connect-offer", dependencies=[Depends(writer)])
    def connect_offer(payload: LiveConnection, request: Request):
        if public_demo or persistent:
            raise HTTPException(403,"Interactive URL configuration is available in a local browser workspace only. Public demos use owner-configured sources.")
        c, source = payload.input, payload.source
        if c.origin != "merchant" or c.kind != "goods" or not payload.exact_variant_confirmed:
            raise HTTPException(422,"Live collection needs a merchant product and confirmation of its exact GTIN/variant")
        if c.unit_cost_net <= 0:
            raise HTTPException(422,"Confirm a positive per-sale cost before adding this retail product")
        with sessions.lock:
            if request.state.session.busy:
                raise HTTPException(409,"Wait until the current collection completes")
            configured = configured_sources(request)
            if len(configured) >= 24:
                raise HTTPException(409,"This workspace is limited to 24 source URLs")
            if any(s.source_id == source.source_id for s in configured):
                raise HTTPException(409,"Source ID already exists")
            for s in configured:
                if s.product_id == source.product_id and (s.expected_gtin.lstrip("0") != source.expected_gtin.lstrip("0") or s.seller.casefold() == source.seller.casefold()):
                    raise HTTPException(409,"Each product must keep one GTIN and one URL per seller")
            entries, _ = request.state.workspace.repository.snapshot()
            existing = next((e for e in entries if e.product.product_id == source.product_id),None)
            if existing and existing.product.retail and existing.product.retail.gtin:
                if existing.product.retail.gtin.lstrip("0") != source.expected_gtin.lstrip("0"):
                    raise HTTPException(422,"The source GTIN must match the exact variant saved for this SKU")
            if c.linked_product_id:
                if c.linked_product_id != source.product_id or not existing or existing.product.data_origin != "merchant":
                    raise HTTPException(422,"Source must match the linked merchant product")
            elif existing:
                raise HTTPException(409,"Choose a new product ID for this business offer")
            else:
                product = Product(product_id=source.product_id,name=c.offer_name,category="Merchant offer",brand=c.business_name,
                    data_origin="merchant",current_price_gross=c.current_price_gross,replacement_cost_net=c.unit_cost_net,
                    vat_rate=c.vat_rate,fee_rate=c.fee_rate,fee_basis=c.fee_basis,minimum_margin=c.minimum_margin,target_margin=c.minimum_margin,
                    inventory=c.test_capacity,sales_30d=0)
                try:
                    request.state.workspace.repository.save_product(product)
                except ConflictError as exc:
                    raise HTTPException(409,str(exc)) from exc
            request.state.session.sources.append(source)
        return {"product_id":source.product_id,"source":source.model_dump(mode="json"),"collected":False,
                "notice":"Source configured for this browser workspace. Run collection to verify support; no price has been fetched yet."}

    @app.get("/api/evidence")
    def evidence(request: Request):
        return request.state.workspace.repository.snapshot()[1]

    @app.post('/api/sources/refresh-product',dependencies=[Depends(writer)])
    async def refresh_product(payload: ProductRefresh,request: Request):
        entries,_=request.state.workspace.repository.snapshot()
        entry=next((e for e in entries if e.product.product_id==payload.product_id),None)
        if entry is None:
            raise HTTPException(404,'Product not found in this workspace')
        if entry.product.data_origin != 'merchant':
            raise HTTPException(422,'The watch-shop example uses simulated offers. Add your own product to collect real prices.')
        selected=[s for s in configured_sources(request) if s.product_id==payload.product_id]
        if not selected:
            raise HTTPException(409,'No source URLs for this product yet. Connect an exact competitor offer first.')
        reserve(request)
        results=[]
        try:
            for source in selected:
                # This rechecks saved identity on every refresh, including static configuration.
                gtin=entry.product.retail.gtin if entry.product.retail else None
                if gtin and gtin.lstrip('0')!=source.expected_gtin.lstrip('0'):
                    results.append(dict(source_id=source.source_id,seller=source.seller,status='failed',message='Configured GTIN does not match the saved variant'))
                    continue
                result=await asyncio.to_thread(collector.collect,source)
                if result['status']=='collected':
                    observation=Observation.model_validate(result['observation'])
                    if observation.product_id!=payload.product_id:
                        raise HTTPException(422,'Collected product does not match the requested SKU')
                    try:
                        request.state.workspace.repository.add_observation(observation,expected_product_version=entry.version,allow_existing=True)
                    except ConflictError as exc:
                        result=dict(source_id=source.source_id,status='failed',message=str(exc))
                results.append({**result,'seller':source.seller})
            return dict(product_id=payload.product_id,results=results,
                        collected=sum(r['status']=='collected' for r in results),
                        failed=sum(r['status']=='failed' for r in results),
                        automatic_scope='Configured exact product URLs only; costs and private sales are not scraped')
        finally:
            request.state.session.busy=False

    @app.post("/api/demo/replay",dependencies=[Depends(writer)])
    async def replay(request: Request):
        reserve(request)
        async def events():
            try:
                yield event({"type":"start","mode":"demo","message":"Replaying a simulated market event for Kiez & Co."})
                for offer in replay_offers(load_demo().as_of):
                    request.state.workspace.repository.add_observation(offer)
                    yield event({"type":"offer","mode":"demo","product_id":offer.product_id,
                                 "seller":offer.seller,"price":str(offer.price_gross),"message":"Simulated offer received"})
                    await asyncio.sleep(.12)
                yield event({"type":"complete","mode":"demo","message":"12 demo offers added. Recalculate the pricing review."})
            finally:
                request.state.session.busy=False
        return StreamingResponse(events(),media_type="text/event-stream",headers={"X-Accel-Buffering":"no"})

    @app.post("/api/demo/reset",dependencies=[Depends(writer)])
    async def reset(request: Request):
        reserve(request)
        session=request.state.session
        try:
            previous=session.service
            session.service=demo_service()
            session.sources=[]
            previous.repository.close()
            return {"status":"reset"}
        finally:
            session.busy=False

    @app.post("/api/sources/collect",dependencies=[Depends(writer)])
    async def collect(request: Request):
        configured = configured_sources(request)
        if not configured:
            raise HTTPException(409,"No live sources configured. Add verified product URLs and GTINs to the server's source configuration first.")
        reserve(request)
        async def events():
            try:
                entries,_=request.state.workspace.repository.snapshot()
                known={e.product.product_id for e in entries}
                yield event({"type":"start","mode":"live","message":"Collecting configured competitor offers"})
                for source in configured:
                    if source.product_id not in known:
                        yield event({"type":"source","status":"failed","source_id":source.source_id,"message":"Product is missing from this workspace"})
                        continue
                    yield event({"type":"progress","mode":"live","source_id":source.source_id,"message":"Checking source policy and offer data"})
                    result=await asyncio.to_thread(collector.collect,source)
                    if result["status"]=="collected":
                        try:
                            request.state.workspace.repository.add_observation(Observation.model_validate(result["observation"]))
                        except ConflictError:
                            pass  # Cached observation already in this session; idempotent.
                    yield event({"type":"source","mode":"live",**result})
                yield event({"type":"complete","mode":"live","message":"Collection finished. Failed sources were not imported."})
            finally:
                request.state.session.busy=False
        return StreamingResponse(events(),media_type="text/event-stream",headers={"X-Accel-Buffering":"no"})

    @app.get("/")
    def index():
        return FileResponse(STATIC / "index.html")

    app.mount("/static", StaticFiles(directory=STATIC), name="static")
    return app


app = create_app()
