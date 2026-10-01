"""Preview, import, inspect and plan: never publishes a price to a store."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from src.api.v1 import get_service, require_writer
from src.application.retail import analyze, workspace, Snapshot
from src.application.retail_import import FIELDS, inspect_csv, preview, commit
from src.domain.retail_import import CSVInspection, ImportPreview, ImportCommit, RetailAnalysis
from src.domain.models import Contract, Product, CatalogEntry
from src.infrastructure.repository import ConflictError

router=APIRouter(prefix="/api/v1/retail",tags=["Retailer workspace"])


@router.get('/workspace')
def shop(service=Depends(get_service)):
    return workspace(service.repository)


@router.post('/analyze')
def analysis(payload:RetailAnalysis,service=Depends(get_service)):
    snapshot=Snapshot(service.repository)
    entry=next((e for e in snapshot.data[0] if e.product.product_id==payload.product_id),None)
    if entry is None:
        raise HTTPException(404,"This product is no longer in your workspace")
    if payload.expected_version is not None and entry.version != payload.expected_version:
        raise HTTPException(409,"Product inputs changed; reload this product before continuing")
    if payload.product_draft:
        if payload.expected_version is None:
            raise HTTPException(422,"A draft preview needs the saved product version")
        if payload.product_draft.product_id != entry.product.product_id or payload.product_draft.data_origin != entry.product.data_origin:
            raise HTTPException(422,"Keep the draft SKU and data origin unchanged")
        previous, proposed = entry.product.retail, payload.product_draft.retail
        if previous and any(o.product_id == payload.product_id for o in snapshot.data[1]):
            if not proposed or (previous.gtin, previous.variant) != (proposed.gtin, proposed.variant):
                raise HTTPException(422,"Use a new SKU to preview another variant; existing market evidence belongs to this SKU")
        entry=CatalogEntry(product=payload.product_draft,version=entry.version)
        snapshot.data=([entry if e.product.product_id==payload.product_id else e for e in snapshot.data[0]],snapshot.data[1])
    try:
        options=payload.model_dump(exclude={'product_id','candidate_price','product_draft','expected_version','comparables'})
        return analyze(entry,snapshot,**options,candidate=payload.candidate_price,
                       comparables=payload.comparables,draft=payload.product_draft is not None)
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc


@router.post('/import/inspect')
def inspect_file(payload:CSVInspection):
    try:
        headers,rows=inspect_csv(payload)
        return dict(headers=headers,row_count=len(rows),sample=rows[:3],
                    fields=[dict(key=k,label=label,required=mandatory) for k,label,mandatory in FIELDS])
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc


@router.post('/import/preview')
def preview_file(payload:ImportPreview,service=Depends(get_service)):
    try:
        return preview(payload,service.repository)[0]
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc


@router.post('/import/commit',dependencies=[Depends(require_writer)],status_code=201)
def import_file(payload:ImportCommit,service=Depends(get_service)):
    try:
        return commit(payload.source,service.repository,payload.fingerprint,payload.confirmed)
    except ConflictError as exc:
        raise HTTPException(409,str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc


class RetailSave(Contract):
    product:Product
    expected_version:int=Field(default=0,ge=0)


@router.put('/product',dependencies=[Depends(require_writer)])
def save_product(payload:RetailSave,service=Depends(get_service)):
    p=payload.product
    if not p.retail:
        raise HTTPException(422,"Use the detailed order costs for retailer inputs")
    entries,observations=service.repository.snapshot()
    previous=next((e.product for e in entries if e.product.product_id==p.product_id),None)
    if (previous and previous.data_origin!=p.data_origin) or (not previous and p.data_origin!='merchant'):
        raise HTTPException(422,"Keep demo and merchant provenance separate")
    if previous and previous.retail and any(o.product_id==p.product_id for o in observations):
        if (previous.retail.gtin,previous.retail.variant)!=(p.retail.gtin,p.retail.variant):
            raise HTTPException(422,"This SKU already has market evidence. Use a new SKU for a different variant or GTIN")
    try:
        return service.repository.save_product(p,payload.expected_version)
    except ConflictError as exc:
        raise HTTPException(409,str(exc)) from exc
