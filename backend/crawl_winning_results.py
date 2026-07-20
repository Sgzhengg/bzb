"""
中标结果数据采集脚本 (b2b.10086.cn API)
使用 b2b.10086.cn queryList/queryDetail API 采集中国移动中标公示

用法:
    python crawl_winning_results.py                           # 默认：全国
    python crawl_winning_results.py --province 广东
    python crawl_winning_results.py --province 广东,广西
"""
import ssl, sys, os, json, logging, argparse, time, base64, re
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ═══════════════════════════════════════════════════════════
# b2b.10086.cn API 配置
# ═══════════════════════════════════════════════════════════
_ctx = ssl.create_default_context()
_ctx.check_hostname = False
_ctx.verify_mode = ssl.CERT_NONE
_ctx.options |= 0x4

B2B_LIST_API = "https://b2b.10086.cn/api-b2b/api-sync-es/white_list_api/b2b/publish/queryList"
B2B_DETAIL_API = "https://b2b.10086.cn/api-b2b/api-sync-es/white_list_api/b2b/publish/queryDetail"
B2B_HEADERS = {
    "Content-Type": "application/json",
    "userloginname": "-1",
    "processinstid": "-1",
    "User-Agent": "Mozilla/5.0",
}

# b2b 搜索关键词（中标结果相关）
B2B_WINNING_KEYWORDS = [
    "中选候选人", "中标候选人", "中选结果", "成交结果",
    "中标结果", "比选结果", "询价结果", "采购结果",
]

# ═══════════════════════════════════════════════════════════
# b2b.10086.cn API 方法
# ═══════════════════════════════════════════════════════════

def _get_http():
    import httpx
    return httpx.Client(
        transport=httpx.HTTPTransport(verify=_ctx),
        timeout=httpx.Timeout(30),
    )


def b2b_search(keyword: str, page: int = 1, size: int = 20) -> list:
    """搜索 b2b.10086.cn 公告列表。"""
    try:
        http = _get_http()
        r = http.post(B2B_LIST_API, json={
            "name": keyword,
            "publishType": "PROCUREMENT",
            "size": size,
            "current": page,
            "sfactApplColumn5": "PC",
        }, headers=B2B_HEADERS)
        if r.status_code == 200:
            return r.json().get("data", {}).get("content", [])
    except Exception as e:
        logger.debug(f"b2b search error [{keyword}]: {e}")
    return []


def b2b_get_detail(publish_id, publish_uuid) -> dict:
    """获取 b2b.10086.cn 公告详情。"""
    try:
        http = _get_http()
        r = http.post(B2B_DETAIL_API, json={
            "publishId": publish_id,
            "publishUuid": publish_uuid,
            "publishType": "PROCUREMENT",
            "sfactApplColumn5": "PC",
        }, headers=B2B_HEADERS)
        if r.status_code == 200:
            return r.json().get("data", {})
    except Exception as e:
        logger.debug(f"b2b detail error: {e}")
    return {}


def b2b_decode_pdf(b64: str) -> str:
    """解码 PDF base64 → 纯文本。"""
    if not b64:
        return ""
    try:
        pdf_bytes = base64.b64decode(b64)
        import fitz
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        texts = [doc[i].get_text() for i in range(len(doc))]
        doc.close()
        return "\n".join(t for t in texts if t.strip())
    except Exception as e:
        logger.debug(f"PDF decode: {e}")
        return ""


def b2b_is_winning_result(item: dict) -> bool:
    """判断是否为中标结果类型。"""
    ptype = item.get("publishOneType", "")
    name = item.get("name", "")
    return (
        any(t in ptype for t in ["CANDIDATE", "RESULT"])
        or any(kw in name for kw in ["中选", "中标", "成交", "候选人", "结果公示", "中选结果", "中标结果"])
    )


# ═══════════════════════════════════════════════════════════
# 中标方提取
# ═══════════════════════════════════════════════════════════

def extract_winners_from_pdf(pdf_text: str) -> list:
    """从 PDF 正文提取中标方列表 [{"name": str, "discount": float|None}]"""
    if not pdf_text or len(pdf_text) < 100:
        return []

    winners = []

    # 方法1：正则匹配 "第X中选候选人：公司名" 或 "中选人：公司名"
    for pat in [
        r'第[一二三四五六七八九十\d]+中选候选[人方][：:]\s*(.+?)(?:[。，\n]|$)',
        r'中选[人方][：:]\s*(.+?)(?:[。，\n]|$)',
        r'中标[人方][：:]\s*(.+?)(?:[。，\n]|$)',
        r'成交供应商[：:]\s*(.+?)(?:[。，\n]|$)',
    ]:
        for m in re.finditer(pat, pdf_text):
            name = m.group(1).strip()
            name = re.sub(r'[（(].*?[）)]', '', name).strip()
            if len(name) >= 4 and len(name) < 60 and "中国移动" not in name:
                if not any(w["name"] == name for w in winners):
                    winners.append({"name": name, "discount": None})

    # 方法2：提取折扣率
    disc_patterns = [
        r'(?:折扣率|折扣|中标折扣|应答折扣)[：:]\s*(\d+\.?\d*)\s*%',
        r'(\d+\.?\d*)\s*%\s*(?:折扣|中标折扣)',
    ]
    for pat in disc_patterns:
        for m in re.finditer(pat, pdf_text):
            disc = float(m.group(1))
            if 1 <= disc <= 100:
                # 将折扣率关联到最近的中标方
                if winners:
                    # 找最近的未设置折扣率的
                    for w in reversed(winners):
                        if w["discount"] is None:
                            w["discount"] = round(disc, 1)
                            break

    # 方法3：LLM 提取（仅在正则不足时）
    if not winners:
        try:
            import httpx as hx
            from app.core.config import settings as app_settings

            prompt = f"""从以下中标公示中提取所有中标公司名称。
返回JSON数组: [{{"name":"公司名"}}]

{pdf_text[:2500]}

只回复JSON数组。"""
            http = hx.Client(
                transport=hx.HTTPTransport(verify=_ctx),
                timeout=hx.Timeout(15),
            )
            r = http.post(
                f"{app_settings.LLM_API_BASE}/chat/completions",
                headers={"Authorization": f"Bearer {app_settings.LLM_API_KEY}", "Content-Type": "application/json"},
                json={"model": app_settings.LLM_MODEL, "temperature": 0, "max_tokens": 400,
                      "messages": [{"role": "user", "content": prompt}]},
            )
            result = r.json()["choices"][0]["message"]["content"]
            m = re.search(r'\[.*\]', result, re.DOTALL)
            if m:
                llm_winners = json.loads(m.group())
                for w in llm_winners:
                    name = w.get("name", "").strip()
                    if name and len(name) >= 4 and len(name) < 60 and "中国移动" not in name:
                        winners.append({"name": name, "discount": None})
        except Exception as e:
            logger.debug(f"LLM winner extract: {e}")

    return winners


# ═══════════════════════════════════════════════════════════
# 省份过滤
# ═══════════════════════════════════════════════════════════

def matches_province(title: str, provinces: list) -> bool:
    """检查标题是否匹配指定省份。"""
    if not provinces:
        return True
    for p in provinces:
        p_short = p.replace("省", "").replace("市", "")
        if p in title or p_short in title:
            return True
    return False


# ═══════════════════════════════════════════════════════════
# 主采集逻辑
# ═══════════════════════════════════════════════════════════

def crawl_b2b_winning(province: str = "") -> dict:
    """从 b2b.10086.cn 采集中标结果。"""
    provinces = [p.strip() for p in province.split(",") if p.strip()] if province else []
    province_label = province or "全国"

    logger.info(f"=== b2b.10086.cn 中标采集: {province_label} ===")

    all_items = []
    seen_ids = set()

    for kw in B2B_WINNING_KEYWORDS:
        for page in range(1, 4):
            items = b2b_search(kw, page)
            if not items:
                break

            new_count = 0
            for item in items:
                pid = str(item.get("id", ""))
                if not pid or pid in seen_ids:
                    continue
                if not b2b_is_winning_result(item):
                    continue

                title = item.get("name", "")
                if not matches_province(title, provinces):
                    continue

                seen_ids.add(pid)
                all_items.append(item)
                new_count += 1

            if new_count > 0:
                logger.info(f"  [{kw}] page {page}: +{new_count}")
            if len(items) < 20:
                break
        time.sleep(0.3)

    # 去重（按ID）
    unique_items = []
    seen = set()
    for item in all_items:
        pid = str(item.get("id", ""))
        if pid not in seen:
            seen.add(pid)
            unique_items.append(item)

    logger.info(f"  共找到 {len(unique_items)} 条中标公示")

    # ── 获取详情 + 提取中标方 ──
    results = []
    for item in unique_items:
        pid = str(item.get("id", ""))
        puid = item.get("uuid", "")
        title = item.get("name", "")
        ptype = item.get("publishOneType", "")
        pub_date = item.get("publishDate", "")

        logger.info(f"  📄 [{ptype}] {title[:60]}...")

        detail = b2b_get_detail(pid, puid)
        pdf_text = b2b_decode_pdf(detail.get("noticeContent", ""))
        logger.info(f"     PDF: {len(pdf_text)}字")

        winners = extract_winners_from_pdf(pdf_text)
        if not winners:
            # 无明确中标方，用标题中的信息
            winners = [{"name": "", "discount": None}]

        logger.info(f"     🏆 {len(winners)} 家中标方")

        for w in winners:
            results.append({
                "title": title,
                "project_name": title,
                "winner_name": w.get("name", ""),
                "discount_rate": w.get("discount"),
                "publish_date": pub_date,
                "publish_type": ptype,
                "source_url": f"https://b2b.10086.cn/#/noticeDetail?publishId={pid}&publishUuid={puid}&publishType=PROCUREMENT",
                "data_source": "b2b_10086",
                "adapter": "b2b_10086",
                "original_content": pdf_text[:5000] if pdf_text else "",
            })

        time.sleep(0.3)

    return {
        "adapter": "b2b_10086",
        "adapter_label": "中国移动",
        "province": province_label,
        "total": len(results),
        "items": results,
    }


# ═══════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="中标结果数据采集 (b2b.10086.cn)")
    parser.add_argument("--adapter", default="b2b_10086",
                        choices=["b2b_10086", "telecom", "unicom", "all"],
                        help="运营商 (默认: b2b_10086)")
    parser.add_argument("--province", default="",
                        help="目标省份，逗号分隔，留空=全国")
    args = parser.parse_args()

    # 目前仅 b2b_10086 通过 b2b.10086.cn API 采集；telecom/unicom/all 暂回退
    result = crawl_b2b_winning(args.province)
    total_items = result["total"]

    # ── 保存结果 ──
    province_slug = args.province.replace(",", "_") if args.province else "quanguo"
    output = {
        "crawl_time": datetime.now().isoformat(),
        "source": "b2b.10086.cn",
        "adapter": args.adapter,
        "province": args.province or "全国",
        "total_items": total_items,
        "adapters": [result],
    }

    output_path = os.path.join(OUTPUT_DIR, f"winning_results_{args.adapter}_{province_slug}.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    logger.info(f"=== 采集完成: 共 {total_items} 条 ===")
    logger.info(f"结果保存至: {output_path}")

    print("\n" + "=" * 70)
    print(f"✅ 中标结果采集汇总 (b2b.10086.cn × {args.province or '全国'}):")
    print("=" * 70)
    print(f"  [中国移动] {total_items} 条")
    print()


if __name__ == "__main__":
    main()
