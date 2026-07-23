"""
中标结果数据采集脚本 (b2b.10086.cn API)
使用 b2b.10086.cn queryList/queryDetail API 采集中国移动中标公示

用法:
    python crawl_winning_results.py                           # 默认：全国
    python crawl_winning_results.py --province 广东
    python crawl_winning_results.py --province 广东,广西
"""
import ssl, sys, os, json, logging, argparse, time, base64, re
import httpx
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
# 广告关键词（用于过滤非广告类中标结果）
# ═══════════════════════════════════════════════════════════
AD_KEYWORDS = [
    "广告", "宣传", "品牌", "活动策划", "新媒体", "视频制作",
    "营销", "设计", "物料", "推广", "传播", "策划", "会展",
    "发布", "创意", "公关", "媒介", "视觉", "拍摄", "制作",
    "印刷", "展示", "展览", "路演", "地推", "促销",
]

AD_EXCLUDE = [
    "基站建设", "光缆铺设", "软件开发", "系统编码", "服务器采购",
    "物业管理", "食堂承包", "保安服务", "保洁服务", "设备采购",
    "网络设备", "交换机", "路由器", "机房", "空调", "电梯",
    "消防", "安防", "监理", "土建", "装修", "绿化", "电力",
]


def is_ad_related(title: str) -> bool:
    """判断中标结果是否与广告营销相关"""
    if not title:
        return False
    # 排除非广告类
    for ex in AD_EXCLUDE:
        if ex in title:
            return False
    # 匹配广告关键词
    for kw in AD_KEYWORDS:
        if kw in title:
            return True
    return False


# ═══════════════════════════════════════════════════════════
# 电信中标采集 (caigou.chinatelecom.com.cn)
# ═══════════════════════════════════════════════════════════
TELECOM_API = "https://caigou.chinatelecom.com.cn/portal/base/announcementJoin/queryListNew"
TELECOM_HEADERS = {
    "Content-Type": "application/json;charset=UTF-8",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}


def crawl_telecom_winning(province: str = "") -> dict:
    """从 caigou.chinatelecom.com.cn 采集中标结果（结果公告类型）"""
    provinces = [p.strip() for p in province.split(",") if p.strip()] if province else []
    province_label = province or "全国"

    logger.info(f"=== 中国电信 中标采集: {province_label} ===")

    http = httpx.Client(verify=_ctx, timeout=httpx.Timeout(30))
    results = []
    seen_titles = set()

    # 先 GET 首页获取 Cookie
    try:
        http.get("https://caigou.chinatelecom.com.cn", timeout=15)
    except Exception:
        pass

    for kw in AD_KEYWORDS[:10]:  # 只用前10个关键词避免重复
        for page in range(1, 4):
            try:
                r = http.post(TELECOM_API, json={
                    "pageNum": page,
                    "pageSize": 20,
                    "type": "n0eves",  # 结果公告
                    "name": kw,
                }, headers=TELECOM_HEADERS)
                if r.status_code != 200:
                    break
                data = r.json()
                items = data.get("data", {}).get("pageInfo", {}).get("list", [])
                if not items:
                    break

                new_count = 0
                for item in items:
                    title = item.get("docTitle", "")
                    if title in seen_titles:
                        continue
                    if not is_ad_related(title):
                        continue
                    if provinces and not any(p in title for p in provinces):
                        continue
                    seen_titles.add(title)

                    # 用列表API字段构造正文（详情API 404，列表数据已含足够信息）
                    fields = [
                        item.get("docTitle", ""), item.get("docType", ""),
                        item.get("provinceName", ""), item.get("createDate", ""),
                    ]
                    original_content = " | ".join(f for f in fields if f)[:5000]

                    results.append({
                        "title": title,
                        "project_name": title,
                        "winner_name": "",
                        "discount_rate": None,
                        "publish_date": item.get("createDate", ""),
                        "publish_type": item.get("docType", "结果公告"),
                        "source_url": f"https://caigou.chinatelecom.com.cn/DeclareDetails?id={item.get('docId', item.get('id', ''))}&docTypeCode={item.get('docTypeCode', '')}",
                        "data_source": "telecom",
                        "adapter": "telecom",
                        "original_content": original_content,
                    })
                    new_count += 1

                if new_count > 0:
                    logger.info(f"  [电信:{kw}] page {page}: +{new_count}")
                if len(items) < 20:
                    break
            except Exception as e:
                logger.warning(f"  电信 API 错误 [{kw}]: {e}")
                break
            time.sleep(0.5)

    http.close()
    logger.info(f"  电信共找到 {len(results)} 条广告类中标结果")

    return {
        "adapter": "telecom",
        "adapter_label": "中国电信",
        "province": province_label,
        "total": len(results),
        "items": results,
    }


# ═══════════════════════════════════════════════════════════
# 联通中标采集 (chinaunicombidding.cn)
# ═══════════════════════════════════════════════════════════
UNICOM_API = "https://www.chinaunicombidding.cn/api/v1/bizAnno/getAnnoList"
UNICOM_HEADERS = {
    "Content-Type": "application/json;charset=UTF-8",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}


def crawl_unicom_winning(province: str = "") -> dict:
    """从 chinaunicombidding.cn 采集中标结果"""
    provinces = [p.strip() for p in province.split(",") if p.strip()] if province else []
    province_label = province or "全国"

    logger.info(f"=== 中国联通 中标采集: {province_label} ===")

    http = httpx.Client(timeout=httpx.Timeout(30))
    results = []
    seen_titles = set()

    for kw in AD_KEYWORDS[:10]:
        for page in range(1, 4):
            try:
                r = http.post(UNICOM_API, json={
                    "pageNo": page,
                    "pageSize": 10,
                    "modeNo": "BizAnnoVoMtable",
                    "annoName": kw,
                }, headers=UNICOM_HEADERS)
                if r.status_code != 200:
                    break
                d = r.json()
                if not d.get("success"):
                    break
                records = d.get("data", {}).get("records", [])
                if not records:
                    break

                new_count = 0
                for item in records:
                    title = item.get("annoName", "")
                    atype = item.get("annoType", "")
                    if title in seen_titles:
                        continue
                    # 仅保留中标相关类型
                    if not any(t in atype for t in ["中标", "候选人", "结果", "成交"]):
                        continue
                    if not is_ad_related(title):
                        continue
                    if provinces and not any(p in title for p in provinces):
                        continue
                    seen_titles.add(title)

                    # 用列表API字段构造正文（详情API 404，列表数据已含足够信息）
                    fields = [
                        item.get("annoName", ""), item.get("annoType", ""),
                        item.get("provinceName", ""), item.get("bidCompany", ""),
                        item.get("procurementType", ""), item.get("createDate", ""),
                    ]
                    original_content = " | ".join(f for f in fields if f)[:5000]

                    results.append({
                        "title": title,
                        "project_name": title,
                        "winner_name": item.get("bidCompany", ""),
                        "discount_rate": None,
                        "publish_date": item.get("createDate", ""),
                        "publish_type": atype,
                        "source_url": f"https://www.chinaunicombidding.cn/bidInformation/detail?id={item.get('id','')}",
                        "data_source": "unicom",
                        "adapter": "unicom",
                        "original_content": original_content,
                    })
                    new_count += 1

                if new_count > 0:
                    logger.info(f"  [联通:{kw}] page {page}: +{new_count}")
                if len(records) < 10:
                    break
            except Exception as e:
                logger.warning(f"  联通 API 错误 [{kw}]: {e}")
                break
            time.sleep(0.5)

    http.close()
    logger.info(f"  联通共找到 {len(results)} 条广告类中标结果")

    return {
        "adapter": "unicom",
        "adapter_label": "中国联通",
        "province": province_label,
        "total": len(results),
        "items": results,
    }

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

        # 广告关键词过滤
        if not is_ad_related(title):
            logger.info(f"  ⏭️ 非广告类跳过: {title[:60]}")
            continue

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
    parser = argparse.ArgumentParser(description="中标结果数据采集 (多平台)")
    parser.add_argument("--adapter", default="b2b_10086",
                        choices=["b2b_10086", "telecom", "unicom", "all"],
                        help="运营商 (默认: b2b_10086)")
    parser.add_argument("--province", default="",
                        help="目标省份，逗号分隔，留空=全国")
    args = parser.parse_args()

    province_slug = args.province.replace(",", "_") if args.province else "quanguo"

    if args.adapter == "all":
        # 全部运营商：依次采集移动、电信、联通
        adapters = []
        total_items = 0

        for adapter_name, adapter_label, crawl_fn in [
            ("b2b_10086", "中国移动", crawl_b2b_winning),
            ("telecom", "中国电信", crawl_telecom_winning),
            ("unicom", "中国联通", crawl_unicom_winning),
        ]:
            try:
                result = crawl_fn(args.province)
                adapters.append(result)
                total_items += result["total"]
                logger.info(f"  [{adapter_label}] 采集完成: {result['total']} 条")
            except Exception as e:
                logger.error(f"  [{adapter_label}] 采集失败: {e}")
                adapters.append({
                    "adapter": adapter_name,
                    "adapter_label": adapter_label,
                    "province": args.province or "全国",
                    "total": 0,
                    "items": [],
                })

        output = {
            "crawl_time": datetime.now().isoformat(),
            "source": "多平台采集",
            "adapter": "all",
            "province": args.province or "全国",
            "total_items": total_items,
            "adapters": adapters,
        }

        print("\n" + "=" * 70)
        print(f"[OK] 中标结果采集汇总 (全部运营商 x {args.province or '全国'}):")
        print("=" * 70)
        for a in adapters:
            print(f"  [{a.get('adapter_label', a.get('adapter'))}] {a['total']} 条")
        print(f"  ────────────────────")
        print(f"  总计: {total_items} 条\n")

    else:
        # 单个运营商
        if args.adapter == "telecom":
            result = crawl_telecom_winning(args.province)
        elif args.adapter == "unicom":
            result = crawl_unicom_winning(args.province)
        else:
            result = crawl_b2b_winning(args.province)

        total_items = result["total"]
        output = {
            "crawl_time": datetime.now().isoformat(),
            "source": {
                "b2b_10086": "b2b.10086.cn",
                "telecom": "caigou.chinatelecom.com.cn",
                "unicom": "www.chinaunicombidding.cn",
            }.get(args.adapter, args.adapter),
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


if __name__ == "__main__":
    main()
