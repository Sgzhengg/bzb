"""
客情关系管理 — CRUD API 接口

端点:
  POST   /api/v1/relations                       创建客情记录
  GET    /api/v1/relations                       获取客情列表（筛选+排序）
  GET    /api/v1/relations/{id}                  获取单条详情
  PUT    /api/v1/relations/{id}                  更新客情记录
  DELETE /api/v1/relations/{id}                  删除客情记录
  GET    /api/v1/relations/purchaser/{pid}       按采购方获取客情
  GET    /api/v1/relations/reminders             今日跟进提醒
"""

from datetime import date
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, case, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.client_relation import ClientRelation, Purchaser
from app.schemas.relation import (
    RelationCreate,
    RelationUpdate,
    RelationResponse,
    RelationListResponse,
    ReminderResponse,
    MessageResponse,
    RelationFilterParams,
    RatingEnum,
    RATING_ORDER,
)

router = APIRouter(prefix="/relations", tags=["客情管理"])


# ============================================================
# 辅助：ORM → Response
# ============================================================

def _orm_to_response(record: ClientRelation) -> RelationResponse:
    return RelationResponse.model_validate(record)


# ============================================================
# 辅助：按 S>A>B>C>D 排序的 CASE 表达式
# ============================================================

def _rating_order_case():
    """生成 SQL CASE 表达式用于按评级排序。"""
    return case(
        (ClientRelation.rating == "S", 0),
        (ClientRelation.rating == "A", 1),
        (ClientRelation.rating == "B", 2),
        (ClientRelation.rating == "C", 3),
        (ClientRelation.rating == "D", 4),
        else_=5,
    )


# ============================================================
# 1. POST /api/v1/relations — 创建客情记录
# ============================================================

@router.post(
    "",
    response_model=RelationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建客情记录",
)
async def create_relation(
    body: RelationCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    创建一条新的客情关系记录。

    - **purchaser_id**: 采购方ID（必填）
    - **contact_name**: 联系人姓名（必填）
    - **rating**: 关系评级，S/A/B/C/D，默认C
    - **next_followup_date**: 下次跟进提醒日期，设置后可参与提醒查询
    """
    # 验证采购方是否存在
    purchaser = await db.get(Purchaser, body.purchaser_id)
    if not purchaser:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"采购方ID {body.purchaser_id} 不存在",
        )

    record = ClientRelation(**body.model_dump())
    db.add(record)
    await db.commit()
    await db.refresh(record)

    return _orm_to_response(record)


# ============================================================
# 2. GET /api/v1/relations — 获取客情列表
# ============================================================

@router.get(
    "",
    response_model=RelationListResponse,
    summary="获取客情记录列表",
)
async def list_relations(
    purchaser_id: int = Query(None, description="按采购方ID筛选"),
    rating: RatingEnum = Query(None, description="按评级筛选"),
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(20, ge=1, le=100, description="返回上限"),
    db: AsyncSession = Depends(get_db),
):
    """
    获取客情记录列表，支持按采购方、评级筛选。

    结果按评级从高到低排列（S > A > B > C > D），
    同评级按最近接触时间降序。
    """
    # 构建查询条件
    conditions = []
    if purchaser_id is not None:
        conditions.append(ClientRelation.purchaser_id == purchaser_id)
    if rating is not None:
        conditions.append(ClientRelation.rating == rating.value)

    # 总数
    count_query = select(func.count()).select_from(ClientRelation)
    if conditions:
        count_query = count_query.where(and_(*conditions))
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 列表（按评级排序 + 最近接触时间降序）
    list_query = (
        select(ClientRelation)
        .order_by(_rating_order_case())
        .order_by(ClientRelation.last_contact_date.desc().nullslast())
        .offset(skip)
        .limit(limit)
    )
    if conditions:
        list_query = list_query.where(and_(*conditions))

    result = await db.execute(list_query)
    records = result.scalars().all()

    return RelationListResponse(
        total=total,
        items=[_orm_to_response(r) for r in records],
    )


# ============================================================
# 3. GET /api/v1/relations/reminders — 今日跟进提醒（固定路径必须在前）
# ============================================================

@router.get(
    "/reminders",
    response_model=List[ReminderResponse],
    summary="获取今日跟进提醒",
)
async def get_today_reminders(
    db: AsyncSession = Depends(get_db),
):
    """
    获取所有 next_followup_date 为今天的客情记录。

    结果按评级降序（S > A > B > C > D），
    用于每日跟进提醒。
    """
    today = date.today()

    query = (
        select(ClientRelation)
        .where(ClientRelation.next_followup_date == today)
        .order_by(_rating_order_case())
        .order_by(ClientRelation.last_contact_date.desc().nullslast())
    )
    result = await db.execute(query)
    records = result.scalars().all()

    return [
        ReminderResponse(
            id=r.id,
            purchaser_id=r.purchaser_id,
            contact_name=r.contact_name,
            rating=r.rating,
            next_followup_date=r.next_followup_date,
            last_contact_date=r.last_contact_date,
            title=r.title,
            phone=r.phone,
        )
        for r in records
    ]


# ============================================================
# 4. GET /api/v1/relations/purchaser/{purchaser_id}（固定路径必须在前）
# ============================================================

@router.get(
    "/purchaser/{purchaser_id}",
    response_model=List[RelationResponse],
    summary="按采购方获取客情记录",
)
async def get_relations_by_purchaser(
    purchaser_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    获取指定采购方的全部客情记录。

    结果按评级从高到低排序（S > A > B > C > D）。
    """
    # 先验证采购方存在
    purchaser = await db.get(Purchaser, purchaser_id)
    if not purchaser:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"采购方ID {purchaser_id} 不存在",
        )

    query = (
        select(ClientRelation)
        .where(ClientRelation.purchaser_id == purchaser_id)
        .order_by(_rating_order_case())
        .order_by(ClientRelation.last_contact_date.desc().nullslast())
    )
    result = await db.execute(query)
    records = result.scalars().all()

    return [_orm_to_response(r) for r in records]


# ============================================================
# 5. GET /api/v1/relations/{id} — 获取单条详情
# ============================================================

@router.get(
    "/{relation_id}",
    response_model=RelationResponse,
    summary="获取客情记录详情",
)
async def get_relation(
    relation_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    根据ID获取单条客情记录的完整信息。
    """
    record = await db.get(ClientRelation, relation_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"客情记录 {relation_id} 不存在",
        )
    return _orm_to_response(record)


# ============================================================
# 4. PUT /api/v1/relations/{id} — 更新客情记录
# ============================================================

@router.put(
    "/{relation_id}",
    response_model=RelationResponse,
    summary="更新客情记录",
)
async def update_relation(
    relation_id: int,
    body: RelationUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    更新一条客情记录。只需传入需要修改的字段，未传入的字段保持不变。

    如果修改了 purchaser_id，会验证新采购方是否存在。
    """
    record = await db.get(ClientRelation, relation_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"客情记录 {relation_id} 不存在",
        )

    update_data = body.model_dump(exclude_unset=True)

    # 验证采购方
    if "purchaser_id" in update_data:
        purchaser = await db.get(Purchaser, update_data["purchaser_id"])
        if not purchaser:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"采购方ID {update_data['purchaser_id']} 不存在",
            )

    for key, value in update_data.items():
        setattr(record, key, value)

    await db.commit()
    await db.refresh(record)

    return _orm_to_response(record)


# ============================================================
# 5. DELETE /api/v1/relations/{id} — 删除客情记录
# ============================================================

@router.delete(
    "/{relation_id}",
    response_model=MessageResponse,
    summary="删除客情记录",
)
async def delete_relation(
    relation_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    删除一条客情记录。

    - 成功返回确认消息
    - 记录不存在返回 404
    """
    record = await db.get(ClientRelation, relation_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"客情记录 {relation_id} 不存在",
        )

    await db.delete(record)
    await db.commit()

    return MessageResponse(
        message="删除成功",
        detail=f"已删除客情记录 {relation_id}（{record.contact_name}）",
    )
