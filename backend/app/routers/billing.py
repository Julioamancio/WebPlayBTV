from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlmodel import Session, select

from app.config import STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET
from app.db import get_session
from app.models import License, AuditLog
from app.models_auth import UserAccount
from app.routers.auth import get_current_user, UserProfile

try:
    import stripe  # type: ignore
except Exception:  # pragma: no cover
    stripe = None


router = APIRouter(prefix="/billing", tags=["billing"])


class CheckoutRequest(BaseModel):
    price_id: str
    success_url: str
    cancel_url: str


class CheckoutResponse(BaseModel):
    session_id: str
    url: str


class PortalRequest(BaseModel):
    return_url: str


class PortalResponse(BaseModel):
    url: str


class SubscriptionInfo(BaseModel):
    id: str
    status: str
    plan: str | None = None


@router.post("/checkout", response_model=CheckoutResponse)
def create_checkout_session(
    payload: CheckoutRequest,
    current_user: UserProfile = Depends(get_current_user),
):
    if stripe is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Stripe SDK não disponível")
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="STRIPE_SECRET_KEY ausente na configuração")

    stripe.api_key = STRIPE_SECRET_KEY

    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": payload.price_id, "quantity": 1}],
            client_reference_id=current_user.username,
            success_url=payload.success_url,
            cancel_url=payload.cancel_url,
        )
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Erro ao criar sessão: {e}")

    return CheckoutResponse(session_id=session.get("id"), url=session.get("url"))


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    response: Response,
    session: Session = Depends(get_session),
):
    if stripe is None:
        # Aceita, mas não processa
        return {"status": "ok", "processed": False}
    if not STRIPE_WEBHOOK_SECRET:
        # Sem segredo configurado: não valida, evita processar
        return {"status": "ok", "processed": False}

    payload = await request.body()
    sig_header = request.headers.get("Stripe-Signature")
    if not sig_header:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Stripe-Signature ausente")

    try:
        event = stripe.Webhook.construct_event(payload=payload, sig_header=sig_header, secret=STRIPE_WEBHOOK_SECRET)
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Webhook inválido: {e}")

    event_type: str = event.get("type", "")
    data_object = event.get("data", {}).get("object", {})

    # Processa checkout.session.completed: cria/ativa licença para o usuário do client_reference_id
    if event_type == "checkout.session.completed":
        username: Optional[str] = data_object.get("client_reference_id")
        subscription_id: Optional[str] = data_object.get("subscription")
        customer_id: Optional[str] = data_object.get("customer")

        if not username:
            return {"status": "ignored", "reason": "missing_client_reference_id"}

        plan_value: Optional[str] = None
        if subscription_id and STRIPE_SECRET_KEY:
            try:
                stripe.api_key = STRIPE_SECRET_KEY
                sub = stripe.Subscription.retrieve(subscription_id)
                # usa o primeiro item da assinatura
                items = sub.get("items", {}).get("data", [])
                if items:
                    price = items[0].get("price", {})
                    plan_value = price.get("id") or price.get("nickname") or price.get("product")
            except Exception:
                plan_value = None

        # Se houver customer_id, persistir no UserAccount
        if username and customer_id:
            user = session.exec(select(UserAccount).where(UserAccount.username == username)).first()
            if user:
                user.stripe_customer_id = customer_id
                session.add(user)
                session.commit()

        # upsert pela subscription (external_id); se existir, atualiza
        lic = None
        if subscription_id:
            lic = session.exec(select(License).where(License.external_id == subscription_id)).first()
        if not lic:
            # fallback: busca por licença ativa do usuário
            lic = session.exec(
                select(License).where(License.owner_username == username, License.status == "active")
            ).first()
        if not lic:
            lic = License(owner_username=username, status="active", plan=plan_value, external_id=subscription_id)
            session.add(lic)
            session.commit()
            session.refresh(lic)
            session.add(
                AuditLog(
                    actor_username=username,
                    action="license.create",
                    resource="license",
                    resource_id=lic.id,
                    details=(plan_value or ""),
                )
            )
            session.commit()
        else:
            lic.external_id = subscription_id or lic.external_id
            lic.plan = plan_value
            session.add(lic)
            session.commit()
            session.add(
                AuditLog(
                    actor_username=username,
                    action="license.plan.update",
                    resource="license",
                    resource_id=lic.id,
                    details=(plan_value or ""),
                )
            )
            session.commit()

        response.status_code = status.HTTP_200_OK
        return {"status": "ok"}

    # Atualização de assinatura: ajusta status/plano
    if event_type == "customer.subscription.updated":
        subscription_id: Optional[str] = data_object.get("id")
        status_value: Optional[str] = data_object.get("status")
        plan_value: Optional[str] = None
        items = data_object.get("items", {}).get("data", [])
        if items:
            price = items[0].get("price", {})
            plan_value = price.get("id") or price.get("nickname") or price.get("product")
        # customer pode estar presente
        customer_id: Optional[str] = data_object.get("customer")

        lic = None
        if subscription_id:
            lic = session.exec(select(License).where(License.external_id == subscription_id)).first()
        if lic:
            # status mapping: active/trialing -> active; canceled/unpaid/past_due/incomplete_expired -> inactive
            inactive_statuses = {"canceled", "unpaid", "past_due", "incomplete_expired", "paused"}
            lic.status = "inactive" if (status_value in inactive_statuses) else "active"
            if plan_value:
                lic.plan = plan_value
            session.add(lic)
            session.commit()
            # se conhecemos o owner, podemos atualizar stripe_customer_id
            if customer_id and lic.owner_username:
                user = session.exec(select(UserAccount).where(UserAccount.username == lic.owner_username)).first()
                if user and not user.stripe_customer_id:
                    user.stripe_customer_id = customer_id
                    session.add(user)
                    session.commit()
            session.add(
                AuditLog(
                    actor_username=lic.owner_username,
                    action="license.subscription.update",
                    resource="license",
                    resource_id=lic.id,
                    details=f"status={status_value}, plan={(plan_value or '')}",
                )
            )
            session.commit()
        return {"status": "ok"}

    # Cancelamento/exclusão da assinatura: inativa licença vinculada
    if event_type == "customer.subscription.deleted":
        subscription_id: Optional[str] = data_object.get("id")
        lic = None
        if subscription_id:
            lic = session.exec(select(License).where(License.external_id == subscription_id)).first()
        if lic:
            lic.status = "inactive"
            session.add(lic)
            session.commit()
            session.add(
                AuditLog(
                    actor_username=lic.owner_username,
                    action="license.subscription.deleted",
                    resource="license",
                    resource_id=lic.id,
                    details=(subscription_id or ""),
                )
            )
            session.commit()
        return {"status": "ok"}

    # Outros eventos são ignorados
    return {"status": "ignored", "event_type": event_type}


@router.post("/portal", response_model=PortalResponse)
def create_billing_portal_session(
    payload: PortalRequest,
    current_user: UserProfile = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    if stripe is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Stripe SDK não disponível")
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="STRIPE_SECRET_KEY ausente na configuração")

    user = session.exec(select(UserAccount).where(UserAccount.username == current_user.username)).first()
    if not user or not user.stripe_customer_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cliente Stripe não associado ao usuário")

    stripe.api_key = STRIPE_SECRET_KEY
    try:
        portal = stripe.billing_portal.Session.create(customer=user.stripe_customer_id, return_url=payload.return_url)
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Erro ao criar sessão do portal: {e}")

    return PortalResponse(url=portal.get("url"))


@router.get("/subscription/me", response_model=list[SubscriptionInfo])
def list_my_subscriptions(
    current_user: UserProfile = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    if stripe is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Stripe SDK não disponível")
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="STRIPE_SECRET_KEY ausente na configuração")

    user = session.exec(select(UserAccount).where(UserAccount.username == current_user.username)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")
    if not user.stripe_customer_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Usuário não possui customer do Stripe associado")

    stripe.api_key = STRIPE_SECRET_KEY
    try:
        subs = stripe.Subscription.list(customer=user.stripe_customer_id, status="all", limit=10)
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Erro ao listar assinaturas: {e}")

    items: list[SubscriptionInfo] = []
    for s in subs.get("data", []) or []:
        plan_value = None
        data_items = s.get("items", {}).get("data", [])
        if data_items:
            price = data_items[0].get("price", {})
            plan_value = price.get("id") or price.get("nickname") or price.get("product")
        items.append(SubscriptionInfo(id=s.get("id"), status=s.get("status"), plan=plan_value))

    return items
