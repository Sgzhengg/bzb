"""
b2b.10086.cn 终极采集脚本

完整链路：
  queryList API → 过滤广东移动 → queryDetail API → PDF解码 → LLM分类+预算 → 入库
"""
import ssl, sys, os, base64, logging, time
from urllib.parse import quote
# 确保工作目录在 backend/，否则 sqlite+aiosqlite:///./biaozhongbao.db 找不到表
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import httpx
from datetime import date

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("b2b_final")

# ── SSL + HTTP ──
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
ctx.options |= 0x4
http = httpx.Client(transport=httpx.HTTPTransport(verify=ctx), timeout=30)

HEADERS = {"Content-Type": "application/json", "userloginname": "-1", "processinstid": "-1", "User-Agent": "Mozilla/5.0"}

QUERY_LIST = "https://b2b.10086.cn/api-b2b/api-sync-es/white_list_api/b2b/publish/queryList"
QUERY_DETAIL = "https://b2b.10086.cn/api-b2b/api-sync-es/white_list_api/b2b/publish/queryDetail"

SEARCH_KW = ["广告", "宣传", "活动策划", "品牌推广", "物料制作", "视频制作",
             "新媒体", "媒介投放", "营销策划", "设计制作", "客户活动",
             "路演", "展会", "印刷品", "喷绘", "门头", "营业厅", "渠道推广", "网格营销"]

# 全局：跟踪已有结果公示的项目及结果URL
_result_projects = set()
_result_urls = {}


def search(kw, page=1, size=20):
    try:
        r = http.post(QUERY_LIST, json={"name": kw, "publishType": "PROCUREMENT", "size": size, "current": page, "sfactApplColumn5": "PC"}, headers=HEADERS)
        return r.json().get("data", {}).get("content", []) if r.status_code == 200 else []
    except: return []


def get_detail(publish_id, publish_uuid):
    try:
        r = http.post(QUERY_DETAIL, json={"publishId": publish_id, "publishUuid": publish_uuid, "publishType": "PROCUREMENT", "sfactApplColumn5": "PC"}, headers=HEADERS)
        return r.json().get("data", {}) if r.status_code == 200 else {}
    except: return {}


def decode_pdf(b64: str) -> tuple[str, str]:
    """解码PDF，返回 (纯文本, HTML)。纯文本用于LLM分类，HTML用于前端展示。"""
    if not b64:
        return "", ""
    try:
        pdf_bytes = base64.b64decode(b64)
        import fitz
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        plain_texts = [doc[i].get_text() for i in range(len(doc))]
        html_texts = [doc[i].get_text("html") for i in range(len(doc))]
        doc.close()
        plain = "\n".join(t for t in plain_texts if t.strip())
        html = "\n".join(t for t in html_texts if t.strip())
        return plain, html
    except Exception as e:
        logger.debug(f"PDF decode: {e}")
        return "", ""


def is_gd_mobile(title): return any(kw in title for kw in ["广东移动", "中国移动广东", "中国移动通信集团广东"])


def _normalize_category(cat: str) -> str:
    """将LLM分类结果映射到标准赛道名称"""
    mapping = {
        "媒介资源投放": "媒介投放类",
        "媒介投放": "媒介投放类",
        "品牌宣传传播": "品牌策略类",
        "品牌策略": "品牌策略类",
        "创意设计": "创意设计类",
        "活动策划执行": "活动执行类",
        "活动执行": "活动执行类",
        "内容制作": "内容制作类",
        "新媒体运营": "新媒体运营类",
        "渠道营销": "渠道营销类",
    }
    for k, v in mapping.items():
        if k in cat:
            return v
    return cat


def classify(title, content):
    from app.services.keyword_filter import filter_with_llm_fallback
    r = filter_with_llm_fallback(title, content)
    return r["is_ad"], _normalize_category(r.get("category", "")), r.get("classifier", "")


def extract_budget(title, content):
    from app.services.budget_extractor import extract_budget_hybrid
    return extract_budget_hybrid(title, content)


def extract_qualifications(title: str, content: str) -> str:
    """用 LLM 从公告原文中提炼资格要求摘要"""
    if not content or len(content) < 100:
        return ""
    try:
        import httpx as hx, ssl as ssl_mod, json, re, asyncio as aio
        from app.core.config import settings as app_settings
        
        prompt = f"""从以下招标公告中提取投标资格要求，用简洁的要点形式总结（每条不超过30字）。
只需列出关键的资格条件，如：注册资金、资质证书、业绩要求、人员要求等。
如果公告中没有明确的资格要求，回复"无特殊资格要求"。

公告标题：{title}

公告内容：
{content[:3000]}

请用中文回复，每条一行，以"- "开头。"""
        
        ctx_ssl = ssl_mod.create_default_context()
        ctx_ssl.check_hostname = False; ctx_ssl.verify_mode = ssl_mod.CERT_NONE; ctx_ssl.options |= 0x4
        
        async def _call():
            async with hx.AsyncClient(transport=hx.AsyncHTTPTransport(verify=ctx_ssl), timeout=30) as c:
                r = await c.post(f"{app_settings.LLM_API_BASE}/chat/completions",
                    headers={"Authorization": f"Bearer {app_settings.LLM_API_KEY}", "Content-Type": "application/json"},
                    json={"model": app_settings.LLM_MODEL, "temperature": 0, "max_tokens": 400,
                          "messages": [{"role": "user", "content": prompt}]})
                return r.json()["choices"][0]["message"]["content"]
        
        result = aio.run(_call())
        return result.strip()
    except Exception as e:
        logger.debug(f"LLM qualification extract failed: {e}")
        return ""


def save_db(record):
    import asyncio
    from app.db.session import AsyncSessionLocal
    from app.models.announcement import Announcement
    from sqlalchemy import select

    async def _save():
        async with AsyncSessionLocal() as db:
            existing = await db.execute(select(Announcement).where(Announcement.source_url == record["source_url"]))
            ann = existing.scalar_one_or_none()
            if ann:
                if record.get("original_content"):
                    ann.original_content = record["original_content"]
                    ann.original_content_html = record.get("original_content_html") or ""
                    if record.get("qualification_requirements"):
                        ann.qualification_requirements = record["qualification_requirements"]
                    if record.get("budget"):
                        ann.budget = record["budget"]
                    await db.commit()
                    return True
                return False
            db.add(Announcement(
                title=record["title"], purchaser_level=record.get("purchaser_level", ""),
                procurement_method=record.get("procurement_method", "公开招标"),
                budget=record.get("budget"), registration_fee=record.get("registration_fee"),
                deposit=record.get("deposit"), project_category=record.get("project_category", ""),
                announce_date=_pd(record.get("announce_date", "")),
                deadline=_pd(record.get("announce_date", "")),
                qualification_requirements=record.get("qualification_requirements") or "",
                original_content=record.get("original_content", ""),
                original_content_html=record.get("original_content_html") or "",
                source_url=record["source_url"], industry="中国移动通信集团广东有限公司",
                province="广东", city=_city(record.get("title", "")),
            ))
            await db.commit()
            return True
    return asyncio.run(_save())


def _pd(s):
    import re
    m = re.match(r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})", str(s)) if s else None
    return date(int(m[1]), int(m[2]), int(m[3])) if m else date.today()

def _city(t):
    for c in ["广州","深圳","东莞","佛山","惠州","珠海","中山","江门","茂名","揭阳","汕头","湛江","肇庆","梅州","汕尾","河源","阳江","清远","韶关","潮州","云浮"]:
        if c in t: return c
    return ""


def main():
    all_items, seen = [], set()
    all_results = []
    logger.info("=" * 60)
    logger.info("b2b 终极采集: API列表 + queryDetail PDF + LLM分类/预算")
    logger.info("=" * 60)

    # ── 第1轮：通用搜索（全类型）──
    for kw in SEARCH_KW:
        for page in range(1, 4):
            items = search(kw, page)
            if not items: break
            for item in items:
                pid = str(item.get("id", ""))
                if not pid or pid in seen: continue
                if not is_gd_mobile(item.get("name", "")): continue
                seen.add(pid)
                all_items.append(item)
            if len(items) < 20: break

    # ── 第2轮：搜索采购公告类型 ──
    logger.info("--- 第2轮：搜索采购公告 ---")
    for kw in SEARCH_KW[:10]:
        for page in range(1, 3):
            items = search(kw, page)
            if not items: break
            for item in items:
                pid = str(item.get("id", ""))
                if not pid or pid in seen: continue
                ptype = item.get("publishOneType", "")
                if "PROCUREMENT" not in ptype and "采购" not in ptype: continue
                if not is_gd_mobile(item.get("name", "")): continue
                seen.add(pid)
                all_items.append(item)
            if len(items) < 20: break

    # ── 第3轮：大范围搜索采购公告（更大pageSize，更多页）──
    logger.info("--- 第3轮：大范围搜索采购公告 ---")
    broad_kw = ["广东移动", "中国移动广东", "广东有限公司", "分公司"]
    for kw in broad_kw:
        for page in range(1, 4):
            items = search(kw, page, size=50)
            if not items: break
            for item in items:
                pid = str(item.get("id", ""))
                if not pid or pid in seen: continue
                ptype = item.get("publishOneType", "")
                if "CANDIDATE" in ptype or "RESULT" in ptype:
                    continue  # 第1轮已覆盖
                if not is_gd_mobile(item.get("name", "")): continue
                seen.add(pid)
                all_items.append(item)
            if len(items) < 50: break

    # 排序：候选人→结果→其他，确保候选人折扣率先入库
    def _sort_key(item):
        pt = item.get("publishOneType", "")
        if "CANDIDATE" in pt: return 1
        if "RESULT" in pt: return 2
        return 3
    all_items.sort(key=_sort_key)

    for item in all_items:
        process_item(item, all_results)

    logger.info("=" * 60)
    logger.info(f"采集完成: {len(all_results)} 条（采购公告+中选公示）")
    with_b = sum(1 for r in all_results if r.get("budget"))
    with_pdf = sum(1 for r in all_results if len(r.get("original_content","")) > 500)
    logger.info(f"有预算: {with_b}/{len(all_results)} | 有PDF正文: {with_pdf}/{len(all_results)}")


def _simplify_name(title: str) -> str:
    """简化公告名称：去公司前缀+类型后缀"""
    import re
    title = re.sub(r'^中国移动通信集团广东有限公司\s*', '', title)
    title = re.sub(r'^中国移动广东公司\s*', '', title)
    title = re.sub(r'_(?:中选结果|中选候选人|询比|采购|招标|谈判|直接).*$', '', title)
    title = re.sub(r'公开询比采购项目$', '', title)
    title = re.sub(r'公开询比项目$', '', title)
    title = re.sub(r'直接采购项目$', '', title)
    return title.strip()


def process_item(item, all_results):
    """处理单条公告"""
    pid = str(item.get("id", ""))
    puid = item.get("uuid", "")
    original_title = item.get("name", "")
    display_title = _simplify_name(original_title)
    # 添加省公司前缀
    if '分公司' not in display_title:
        display_title = '广东有限公司 ' + display_title
    ptype = item.get("publishOneType", "")

    logger.info(f"  📄 [{ptype}] {display_title[:50]}...")

    detail = get_detail(pid, puid)
    pdf_text, pdf_html = decode_pdf(detail.get("noticeContent", ""))
    full_text = f"{original_title}\n{pdf_text}" if pdf_text else original_title
    logger.info(f"     PDF: {len(pdf_text)}字")

    is_ad, cat, clf = classify(original_title, full_text)
    if not is_ad:
        logger.info(f"     ⏭️ 非广告 [{clf}]")
        return

    budget_info = extract_budget(original_title, full_text)
    qual_req = extract_qualifications(original_title, pdf_text)

    record = {
        "title": display_title, "project_category": cat,
        "budget": budget_info.get("budget"),
        "registration_fee": budget_info.get("registration_fee"),
        "deposit": budget_info.get("deposit"),
        "announce_date": item.get("publishDate", ""),
        "original_content": pdf_text[:50000],
        "original_content_html": pdf_html[:100000],
        "qualification_requirements": qual_req,
        "source_url": f"https://b2b.10086.cn/#/noticeDetail?publishId={pid}&publishUuid={puid}&publishType=PROCUREMENT",
        "purchaser_level": "地市公司" if "分公司" in original_title else "省公司",
    }

    # ── 分流 ──
    is_candidate_or_result = "CANDIDATE" in ptype or "RESULT" in ptype

    if is_candidate_or_result:
        all_results.append(record)
        # 提取全部中标方
        winners = extract_all_winners(pdf_text)
        logger.info(f"     🏆 [{clf}] {cat} | {len(winners)}家中标方 | {len(pdf_text)}字")
        saved = save_all_winners(record, winners, ptype)
        logger.info(f"     💾 → 中标结果 ({saved}条)")
    else:
        all_results.append(record)
        budget_str = f"💰{record['budget']}万" if record.get('budget') else "—"
        logger.info(f"     ✅ [{clf}] {cat} | {budget_str} | {len(pdf_text)}字")
        if save_db(record): logger.info(f"     💾 → 机会列表")

    time.sleep(0.5)


def extract_all_winners(pdf_text: str):
    """从PDF提取全部中标方列表 [{"name": str, "discount": float}, ...]"""
    import json, re
    
    if not pdf_text or len(pdf_text) < 100:
        return []
    
    # 用 LLM 提取
    try:
        import httpx as hx, ssl as ssl_mod
        from app.core.config import settings as app_settings
        
        prompt = f"""从以下中标公示中提取所有中标公司及其折扣率(%)。
返回JSON数组: [{{"name":"公司名", "discount":折扣率数字}}]

{pdf_text[:3000]}

只回复JSON数组，不要其他内容。"""
        
        ctx_ssl = ssl_mod.create_default_context()
        ctx_ssl.check_hostname = False; ctx_ssl.verify_mode = ssl_mod.CERT_NONE; ctx_ssl.options |= 0x4
        
        import asyncio as aio
        
        async def _call():
            async with hx.AsyncClient(transport=hx.AsyncHTTPTransport(verify=ctx_ssl), timeout=15) as c:
                r = await c.post(f"{app_settings.LLM_API_BASE}/chat/completions",
                    headers={"Authorization": f"Bearer {app_settings.LLM_API_KEY}", "Content-Type": "application/json"},
                    json={"model": app_settings.LLM_MODEL, "temperature": 0, "max_tokens": 500,
                          "messages": [{"role": "user", "content": prompt}]})
                return r.json()["choices"][0]["message"]["content"]
        
        result = aio.run(_call())
        # 提取JSON数组
        m = re.search(r'\[.*\]', result, re.DOTALL)
        if m:
            winners = json.loads(m.group())
            # 过滤无效项（discount可为None）
            valid = []
            for w in winners:
                name = w.get("name", "").strip()
                disc = w.get("discount")
                if name and len(name) >= 4 and "中国移动" not in name:
                    valid.append({"name": name, "discount": round(float(disc), 1) if disc is not None else None})
            if valid:
                return valid
    except Exception as e:
        logger.debug(f"LLM winner extract failed: {e}")
    
    # 正则回退：支持"标包X的中选人：1.公司名"格式
    winners = []
    import re
    lines = pdf_text.split('\n')
    for i, line in enumerate(lines):
        # 格式1: 标包X 排序 公司名 折扣率
        if re.match(r'^(第[一二三四五六七八九十]+名|标包\d+)', line.strip()):
            name = ""
            disc = None
            for offset in range(1, 5):
                if i + offset < len(lines):
                    cand = lines[i + offset].strip()
                    cand = re.sub(r'^\d+[\.\、\s]+', '', cand)
                    if not name and len(cand) >= 4 and len(cand) < 50 and '中国移动' not in cand and '份额' not in cand:
                        name = cand
                    if '%' in cand:
                        m2 = re.search(r'(\d+\.?\d*)\s*%', cand)
                        if m2 and 1 <= float(m2.group(1)) <= 99:
                            disc = float(m2.group(1))
            if name:
                winners.append({"name": name, "discount": round(disc, 1) if disc is not None else None})
        
        # 格式2: 标包X的中选人：/ 标包X的中选人为：
        m_simple = re.match(r'标包\d+的中选人[：为]', line.strip())
        if m_simple:
            for offset in range(1, 4):
                if i + offset < len(lines):
                    cand = lines[i + offset].strip()
                    cand = re.sub(r'^\d+[\.\、\s]+', '', cand)
                    if len(cand) >= 4 and len(cand) < 50 and '中国移动' not in cand:
                        winners.append({"name": cand, "discount": None})
    return winners


def save_all_winners(record: dict, winners: list, ptype: str) -> int:
    """保存中标方。结果公示更新链接+替换数据，候选人仅当无结果时保存。"""
    import asyncio
    from sqlalchemy import delete, select, func, update
    from app.db.session import AsyncSessionLocal
    from app.models.historical_award import HistoricalAward
    
    is_result = "RESULT" in ptype
    
    async def _save():
        async with AsyncSessionLocal() as db:
            if is_result:
                # 结果公示：记录URL + 标记项目（阻止候选人保存）
                _result_urls[record["title"]] = record["source_url"]
                _result_projects.add(record["title"])
                if winners:
                    # 删除已有记录（候选人数据），用结果数据替换
                    await db.execute(
                        delete(HistoricalAward).where(
                            HistoricalAward.project_name == record["title"]
                        )
                    )
                else:
                    # 结果无中标方 → 仅更新链接
                    await db.execute(
                        update(HistoricalAward).where(
                            HistoricalAward.project_name == record["title"]
                        ).values(source_url=record["source_url"])
                    )
                    return 0
            else:
                if record["title"] in _result_projects:
                    return 0
                existing = await db.execute(
                    select(func.count()).select_from(HistoricalAward).where(
                        HistoricalAward.project_name == record["title"]
                    )
                )
                if existing.scalar() > 0:
                    return 0
            
            # 候选人：使用结果URL（如果有的话）
            final_url = _result_urls.get(record["title"], record["source_url"])
            
            count = 0
            for w in winners:
                db.add(HistoricalAward(
                    project_name=record["title"], purchaser_id=1,
                    winner_name=w["name"], winner_type="头部常客",
                    bid_amount=0, discount_rate=w["discount"],
                    project_category=record.get("project_category", ""),
                    bid_open_date=_pd(record.get("announce_date", "")),
                    source_url=final_url,
                ))
                count += 1
            await db.commit()
        return count
    return asyncio.run(_save())


if __name__ == "__main__":
    main()
