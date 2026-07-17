"""
中国电信采购平台 (caigou.chinatelecom.com.cn) 爬虫适配器

数据源:
  - 列表: POST /portal/base/announcementJoin/queryListNew (JSON API)
  - 详情: POST /portal/base/announcementJoin/queryDetail (JSON API)
  - 公告类型: xi9s=采购公告, n0eves=结果公告

字段提取:
  - title: API 返回 docTitle
  - province: API 返回 provinceName
  - budget/registration_fee/deposit: 正则从详情正文提取
  - project_category: LLM 分类
  - original_content: 详情页正文全文
"""

import re
import ssl
from typing import List, Dict, Optional, Tuple

import httpx
from bs4 import BeautifulSoup

from .base_adapter import BaseAdapter


class TelecomAdapter(BaseAdapter):
    """中国电信采购平台 (caigou.chinatelecom.com.cn) 适配器"""

    BASE_URL = "https://caigou.chinatelecom.com.cn"
    LIST_API = "https://caigou.chinatelecom.com.cn/portal/base/announcementJoin/queryListNew"
    DETAIL_API = "https://caigou.chinatelecom.com.cn/portal/base/announcementJoin/queryDetail"

    # 公告类型编码 → 名称
    ANNOUNCE_TYPES = {
        "xi9s": "采购公告",
        "n0eves": "结果公告",
    }

    def __init__(self, config: dict = None):
        default_config = {
            "name": "中国电信采购平台",
            "base_url": self.BASE_URL,
            "min_delay": 1.0,
            "max_delay": 2.0,
            "max_retries": 2,
            "timeout": 30,
            "max_pages": 3,
            "search_keyword": "广告 宣传 品牌 活动策划 新媒体 视频制作 营销 设计 物料",
        }
        if config:
            default_config.update(config)
        super().__init__(default_config)

        self._client = None
        self._seen_ids = set()
        self._current_item = None  # 当前正在处理的 telecom item
        # 电信平台关键词匹配在隐藏字段，只用最精准的关键词减少噪音
        self.search_keywords = [
            "广告", "宣传",
        ]

    def get_source_name(self) -> str:
        return "telecom"

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            self._client = httpx.Client(
                transport=httpx.HTTPTransport(verify=ctx),
                timeout=httpx.Timeout(self.timeout),
                follow_redirects=True,
                headers={
                    "Content-Type": "application/json;charset=UTF-8",
                    "User-Agent": self._next_ua(),
                    "Accept": "application/json, text/plain, */*",
                    "Referer": f"{self.BASE_URL}/",
                    "Origin": self.BASE_URL,
                },
            )
        return self._client

    def _ensure_cookies(self):
        """访问首页获取必要的 Cookie（JSESSIONID 等）。"""
        client = self._get_client()
        try:
            resp = client.get(self.BASE_URL + "/", follow_redirects=True)
            self.logger.debug(f"获取 Cookie: HTTP {resp.status_code}")
        except Exception as e:
            self.logger.warning(f"首页访问失败: {e}")

    # ── 列表页 ──

    def fetch_list(self, page: int = 1) -> str:
        """
        通过 JSON API 获取公告列表。

        策略：电信 API 的 name 参数在隐藏字段也匹配（假阳性多），
        但仍需关键词缩小范围（全平台 12000+ 条）。假阳性由 _normalize_record 过滤。
        """
        import json as _json
        client = self._get_client()
        self._ensure_cookies()

        all_items = []
        seen = set()

        # 与移动适配器相同的关键词库，确保覆盖面一致
        self.search_keywords = [
            "广告设计", "品牌推广", "活动策划", "新媒体运营",
            "媒介投放", "视频制作", "创意设计", "品牌宣传",
            "广告代理", "营销策划", "内容制作", "直播运营",
            "广告物料", "宣传品制作", "喷绘制作", "展会搭建",
            "路演活动", "短视频", "H5制作",
            "广告", "宣传", "活动", "品牌", "新媒体", "视频", "物料", "设计",
            "营销", "推广",
        ]

        for kw in self.search_keywords:
            for ann_type in self.ANNOUNCE_TYPES:
                try:
                    self._random_delay()
                    body = {
                        "pageNum": page,
                        "pageSize": 20,
                        "type": ann_type,
                        "name": kw,
                    }
                    resp = client.post(self.LIST_API, json=body)

                    if resp.status_code == 200:
                        data = resp.json()
                        if data.get("code") == 200:
                            page_info = data.get("data", {}).get("pageInfo", {})
                            items = page_info.get("list", [])
                            for item in items:
                                item_id = str(item.get("id", ""))
                                if item_id and item_id not in seen:
                                    seen.add(item_id)
                                    item["_annType"] = ann_type
                                    all_items.append(item)
                except Exception as e:
                    self.logger.debug(f"电信搜索 '{kw}' ({ann_type}): {e}")

        self.logger.info(f"电信 第{page}页: {len(all_items)} 条")
        return _json.dumps(all_items)

    def parse_list(self, html: str, province: str = "") -> List[Dict]:
        """解析 JSON 列表结果。province 参数用于过滤目标省份。"""
        import json as _json
        try:
            items = _json.loads(html)
        except Exception:
            self.logger.warning("JSON 解析失败")
            return []

        results = []
        for item in items:
            item_id = str(item.get("id", ""))
            title = item.get("docTitle", "")

            if not item_id or not title:
                continue
            if item_id in self._seen_ids:
                continue
            self._seen_ids.add(item_id)

            # 跳过明显非电信的公告（API 关键词搜索已做初步过滤）
            if not self._is_telecom(title):
                self.logger.debug(f"  ⏭️ 非电信: {title[:60]}")
                continue

            # 跳过中标公示
            if self._is_winning_announcement(title):
                self.logger.debug(f"  ⏭️ 跳过公示: {title[:60]}")
                continue

            # 跳过明显非广告类公告（设备采购、工程、IT基础设施等）
            if self._is_non_ad_keyword(title):
                self.logger.debug(f"  ⏭️ 非广告类: {title[:60]}")
                continue

            # 省份过滤
            if province and not self._match_province(title, province):
                continue

            pid = item.get("id", "")
            id_encry_str = item.get("idEncryStr", "")
            encry_code = item.get("encryCode", "")
            doc_type_code = item.get("docTypeCode", "")
            security_code = item.get("securityViewCode", "")

            # API 详情 URL（用于程序抓取，已弃用 HTTP 抓取）
            api_detail_url = (
                f"{self.BASE_URL}"
                f"/portal/base/announcementJoin/detail"
                f"?id={pid}"
                f"&idEncryStr={id_encry_str}"
                f"&encryCode={encry_code}"
            )
            # 公开访问 URL（用于前端链接）
            public_url = (
                f"{self.BASE_URL}"
                f"/DeclareDetails"
                f"?id={pid}"
                f"&docTypeCode={doc_type_code}"
                f"&securityViewCode={security_code}"
            )

            results.append({
                "title": title,
                "publish_date": str(item.get("createDate", ""))[:10],
                "detail_url": public_url,
                "api_detail_url": api_detail_url,
                "notice_type": item.get("docType", "采购公告"),
                "province_name": item.get("provinceName", ""),
                "_telecom_item": item,
            })

        self.logger.info(f"电信 列表解析: {len(results)} 条")
        return results

    def _is_telecom(self, title: str) -> bool:
        """判断是否中国电信相关公告。"""
        keywords = [
            "中国电信", "电信股份", "中电信", "电信集团",
            "广东电信", "广西电信", "福建电信", "海南电信",
            "浙江电信", "湖南电信", "安徽电信", "山东电信",
            "江苏电信", "四川电信", "湖北电信", "河南电信",
            "河北电信", "辽宁电信", "江西电信", "陕西电信",
            "山西电信", "云南电信", "贵州电信", "吉林电信",
            "黑龙江电信", "甘肃电信", "内蒙古电信",
            "新疆电信", "西藏电信", "青海电信", "宁夏电信",
            "北京电信", "上海电信", "天津电信", "重庆电信",
            "中电鸿信", "中电信数智", "电信数智",
        ]
        return any(kw in title for kw in keywords)

    def _is_ad_keyword(self, title: str) -> bool:
        """判断标题是否匹配广告类关键词。"""
        return any(kw in title for kw in self.search_keywords)

    def _is_winning_announcement(self, title: str) -> bool:
        """判断是否为中标公示。"""
        patterns = [
            "中选候选人", "中选结果", "中选人",
            "中标候选人", "中标结果", "中标人",
            "成交候选人", "成交结果",
            "_中选", "_中标", "_成交",
            "询比结果公示", "候选人公示",
        ]
        return any(p in title for p in patterns)

    def _is_non_ad_keyword(self, title: str) -> bool:
        """黑名单：标题含以下关键词的明显非广告类公告。"""
        blacklist = [
            "基站", "机房", "光缆", "光纤", "电缆", "配电", "UPS",
            "服务器", "路由器", "交换机", "防火墙", "存储设备",
            "手机终端", "二手手机", "终端采购", "终端设备",
            "云计算", "云服务", "大数据", "数据中心",
            "软件采购", "系统集成", "网络设备", "通信设备",
            "空调", "电源", "蓄电池", "发电机组",
            "车辆", "办公家具", "办公用品", "装修", "物业",
            "维保服务", "代维", "网优", "工程监理", "工程设计",
            "人力资源", "安保服务", "保洁", "食堂",
            "ICT", "物联网", "AI平台", "芯片",
        ]
        return any(kw in title for kw in blacklist)

    def _match_province(self, title: str, province: str) -> bool:
        """检查标题是否匹配指定省份。"""
        province_map = {
            "广东": ["广东", "广州", "深圳", "东莞", "佛山", "珠海", "惠州", "中山", "江门", "汕头", "湛江", "茂名", "肇庆", "梅州", "汕尾", "河源", "阳江", "清远", "韶关", "潮州", "揭阳", "云浮"],
            "广西": ["广西", "南宁", "柳州", "桂林", "玉林", "梧州", "北海", "贵港", "钦州", "百色", "河池", "贺州", "来宾", "崇左", "防城港"],
            "福建": ["福建", "福州", "厦门", "泉州", "漳州", "龙岩", "三明", "南平", "莆田", "宁德"],
            "海南": ["海南", "海口", "三亚", "儋州"],
            "浙江": ["浙江", "杭州", "宁波", "温州", "嘉兴", "湖州", "绍兴", "金华", "衢州", "舟山", "台州", "丽水"],
            "湖南": ["湖南", "长沙", "株洲", "湘潭", "衡阳", "邵阳", "岳阳", "常德"],
            "安徽": ["安徽", "合肥", "芜湖", "蚌埠", "淮南", "马鞍山", "淮北", "铜陵", "安庆", "黄山", "滁州", "阜阳", "宿州", "六安", "亳州", "池州", "宣城"],
            "山东": ["山东", "济南", "青岛", "淄博", "枣庄", "东营", "烟台", "潍坊", "济宁", "泰安", "威海", "日照", "临沂", "德州", "聊城", "滨州", "菏泽"],
            "江苏": ["江苏", "南京", "苏州", "无锡", "常州", "南通", "扬州", "镇江", "泰州", "盐城", "徐州", "淮安", "连云港", "宿迁"],
            "四川": ["四川", "成都", "绵阳", "德阳", "宜宾", "南充"],
            "湖北": ["湖北", "武汉", "宜昌", "襄阳", "荆州"],
            "河南": ["河南", "郑州", "洛阳", "南阳"],
            "北京": ["北京"],
            "上海": ["上海"],
            "重庆": ["重庆"],
            "天津": ["天津"],
        }
        # 支持逗号分隔的多省份
        targets = [p.strip() for p in province.split(",") if p.strip()]
        for target in targets:
            keywords = province_map.get(target, [target])
            if any(kw in title for kw in keywords):
                return True
        return not targets  # 空省份不过滤

    # ── 详情页 ──

    def fetch_detail(self, url: str) -> Tuple[str, Optional[bytes]]:
        """
        构造详情内容用于 LLM/关键词分类。

        策略：电信列表 API 返回了关键字段，但标题常不含广告词（API 在正文中匹配）。
        因此把完整的原始 JSON 字段值拼接成内容，提高关键词命中率。
        """
        title = ""
        content_parts = []

        item = self._current_item if hasattr(self, "_current_item") and self._current_item else {}

        if item:
            title = item.get("docTitle", "")
            # 把所有非空字段值都加入内容（提高关键词命中率）
            for key, val in item.items():
                if isinstance(val, str) and val and not key.startswith("_"):
                    content_parts.append(val)

        if not title:
            title = "未知标题"

        content_text = " ".join(content_parts) if content_parts else title
        return title, content_text.encode("utf-8") if content_text else None

    def parse_detail(self, html: str, pdf_bytes: Optional[bytes] = None) -> Dict:
        """
        解析详情页，提取全部字段。

        html 参数为公告标题（由 fetch_detail 传入）
        pdf_bytes 为详情正文（由 fetch_detail 返回的内容编码）
        """
        title = html or ""
        content_text = ""

        if pdf_bytes:
            try:
                content_text = pdf_bytes.decode("utf-8", errors="replace")
                self.logger.info(f"  详情: {len(content_text)} 字符")
            except Exception as e:
                self.logger.warning(f"  内容解码失败: {e}")

        if not content_text:
            content_text = title

        # ── 正则提取字段 ──
        purchaser = self._extract_purchaser(title, content_text)
        budget = self._extract_budget_regex(content_text)
        deadline = self._extract_deadline(content_text)
        city = self._extract_city(title)
        province = self._extract_province(title)

        return {
            "title": title,
            "purchaser": purchaser,
            "purchaser_level": "省公司" if "分公司" not in title else "地市公司",
            "procurement_method": self._extract_method(content_text),
            "budget": budget,
            "registration_fee": self._extract_reg_fee(content_text),
            "deposit": self._extract_deposit_regex(content_text),
            "publish_date": "",
            "deadline": deadline,
            "content_text": content_text[:50000],
            "source_url": "",
            "bid_number": self._extract_bid_number(content_text),
            "city": city,
            "province": province,
        }

    # ── 主流程 ──

    def run(self, save_to_db: bool = True, **kwargs) -> List[Dict]:
        """执行完整采集流程。"""
        province_filter = kwargs.get("province", "")
        all_results = []
        seen_urls = set()

        self._seen_ids.clear()
        existing_titles = self._load_existing_titles()  # 加载已有标题，跳过重复

        self.logger.info(f"===== {self.name} 开始采集 (省份={province_filter or '不限'}) =====")

        for page in range(1, self.max_pages + 1):
            self.logger.info(f"--- 列表页 第 {page} 页 ---")

            # 计算当前页的进度范围
            page_progress_start = 10 + (page - 1) * 80 // self.max_pages
            page_progress_end = 10 + page * 80 // self.max_pages
            self._report_progress(page_progress_start, f"正在处理第 {page}/{self.max_pages} 页...")

            try:
                html = self.fetch_list(page=page)
                items = self.parse_list(html, province=province_filter)

                if not items:
                    self.logger.info("无更多公告，翻页结束")
                    break

                # 报告当前页的项目数量
                self._report_progress(
                    page_progress_start + 5,
                    f"第 {page} 页找到 {len(items)} 个公告，开始处理详情..."
                )

                for i, item in enumerate(items):
                    # 计算当前项目的进度
                    item_progress = page_progress_start + 5 + (i + 1) * 70 // self.max_pages // len(items)

                    detail_url = item.get("api_detail_url", "")  # 使用API URL抓取（含加密参数）
                    public_url = item.get("detail_url", "")    # 公开URL用于前端展示
                    if not detail_url or detail_url in seen_urls:
                        continue
                    seen_urls.add(detail_url)

                    self._current_item = item.get("_telecom_item", {})

                    # 跳过数据库中已存在的记录
                    title_check = item.get("title", "")
                    if title_check in existing_titles:
                        self.logger.debug(f"  ⏭️ 已存在，跳过: {title_check[:60]}")
                        continue

                    self._report_progress(item_progress, f"处理第 {page} 页第 {i+1}/{len(items)} 个公告...")

                    try:
                        html_detail, pdf_bytes = self.fetch_detail(detail_url)
                        parsed = self.parse_detail(html_detail, pdf_bytes)
                        parsed["source_url"] = public_url  # 前端链接用公开URL
                        parsed["notice_type"] = item.get("notice_type", parsed.get("notice_type", ""))
                        parsed["province"] = parsed["province"] or item.get("province_name", "")
                        parsed["publish_date"] = parsed["publish_date"] or item.get("publish_date", "")

                        record = self._normalize_record(parsed)

                        if record["is_ad"]:
                            all_results.append(record)
                            self.logger.info(
                                f"  ✅ [{i+1}/{len(items)}] {record['title'][:60]} "
                                f"| {record['project_category']}"
                            )
                        else:
                            self.logger.debug(f"  ⏭️ 非广告: {record['title'][:60]}")

                        if save_to_db and record["is_ad"]:
                            self._save_to_db(record)

                    except Exception as e:
                        self.logger.error(f"详情页失败: {detail_url[:80]} - {e}")

            except Exception as e:
                self.logger.error(f"列表页第 {page} 页失败: {e}")
                break

        self.logger.info(f"===== {self.name} 采集完成: {len(all_results)} 条广告类 =====")
        self._report_progress(95, f"采集完成，正在保存 {len(all_results)} 条公告...")
        self.close()
        self._report_progress(100, f"完成！共获取 {len(all_results)} 条公告")
        return all_results

    # ── 字段提取辅助 ──

    def _extract_purchaser(self, title: str, content: str) -> str:
        patterns = [
            r"(中国电信(?:股份|集团)?[^，。；\n]{0,40}(?:有限公司|分公司))",
            r"(中电信[^，。；\n]{0,40}(?:有限公司|分公司))",
        ]
        for pat in patterns:
            m = re.search(pat, title + content)
            if m:
                return m.group(1)
        return ""

    def _extract_budget_regex(self, content: str) -> Optional[float]:
        patterns = [
            r"采购?预算[总]?[金额]?[约]?[：:为]?\s*(\d+(?:\.\d+)?)\s*万",
            r"项目预算[：:]?\s*(\d+(?:\.\d+)?)\s*万",
            r"预算金额[：:]?\s*(\d+(?:\.\d+)?)\s*万",
            r"采购?总?金?额[：:]?\s*(\d+(?:\.\d+)?)\s*万",
            r"最高限价[：:]?\s*(\d+(?:\.\d+)?)\s*万",
            r"估算金额[：:]?\s*(\d+(?:\.\d+)?)\s*万",
        ]
        for pat in patterns:
            m = re.search(pat, content)
            if m:
                return float(m.group(1))
        return None

    def _extract_reg_fee(self, content: str) -> Optional[float]:
        m = re.search(r"(?:招标文件|采购文件|标书)[工]?本?费[：:]\s*(\d+(?:\.\d+)?)\s*元?", content)
        if m:
            val = float(m.group(1))
            return val / 10000 if val > 1000 else val
        return None

    def _extract_deposit_regex(self, content: str) -> Optional[float]:
        m = re.search(r"(?:投标|询价|谈判|磋商)?保证金[：:]\s*(\d+(?:\.\d+)?)\s*万", content)
        if m:
            return float(m.group(1))
        m = re.search(r"(?:投标|询价|谈判|磋商)?保证金[：:]\s*(\d+(?:\.\d+)?)\s*元", content)
        if m:
            return float(m.group(1)) / 10000
        return None

    def _extract_deadline(self, content: str) -> str:
        patterns = [
            r"(\d{4}[-/年]\d{1,2}[-/月]\d{1,2})\s*(?:日)?\s*(?:前|截止|之前)?.*?(?:投标|递交|提交|应答)",
            r"(?:投标|递交|提交|应答).*?截止.*?(\d{4}[-/年]\d{1,2}[-/月]\d{1,2})",
            r"截止时间[：:]\s*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2})",
        ]
        for pat in patterns:
            m = re.search(pat, content)
            if m:
                return m.group(1)
        return ""

    def _extract_method(self, content: str) -> str:
        methods = {
            "公开招标": ["公开招标"],
            "邀请招标": ["邀请招标"],
            "竞争性谈判": ["竞争性谈判"],
            "竞争性磋商": ["竞争性磋商"],
            "询价": ["询价采购", "询价"],
            "单一来源": ["单一来源"],
            "询比": ["公开询比", "询比采购"],
        }
        for method, keywords in methods.items():
            if any(kw in content for kw in keywords):
                return method
        return "公开招标"

    def _extract_bid_number(self, content: str) -> str:
        m = re.search(r"(?:项目|采购)[编号号][：:]\s*([A-Za-z0-9-]+)", content)
        return m.group(1) if m else ""

    def _extract_city(self, title: str) -> str:
        cities = [
            "广州", "深圳", "东莞", "佛山", "珠海", "惠州", "中山", "江门",
            "汕头", "湛江", "茂名", "肇庆", "梅州", "汕尾", "河源", "阳江",
            "清远", "韶关", "潮州", "揭阳", "云浮",
            "南宁", "柳州", "桂林", "玉林", "梧州", "北海", "贵港",
            "钦州", "百色", "河池", "贺州", "来宾", "崇左", "防城港",
            "福州", "厦门", "泉州", "漳州", "龙岩", "三明", "南平", "莆田", "宁德",
            "海口", "三亚", "儋州",
            "杭州", "宁波", "温州", "嘉兴", "湖州", "绍兴", "金华", "衢州", "舟山", "台州", "丽水",
            "长沙", "株洲", "湘潭", "衡阳", "邵阳", "岳阳", "常德",
            "合肥", "芜湖", "蚌埠", "淮南", "马鞍山", "淮北", "铜陵",
            "安庆", "黄山", "滁州", "阜阳", "宿州", "六安", "亳州", "池州", "宣城",
            "济南", "青岛", "淄博", "枣庄", "东营", "烟台", "潍坊",
            "济宁", "泰安", "威海", "日照", "临沂", "德州", "聊城", "滨州", "菏泽",
            "南京", "苏州", "无锡", "常州", "徐州", "南通", "扬州", "镇江",
            "成都", "绵阳", "德阳", "宜宾", "南充",
            "武汉", "宜昌", "襄阳", "荆州",
            "郑州", "洛阳", "开封", "南阳",
            "石家庄", "唐山", "保定", "邯郸",
            "沈阳", "大连", "鞍山", "抚顺",
            "南昌", "赣州", "九江",
            "西安", "宝鸡", "咸阳",
            "太原", "大同", "长治",
            "昆明", "曲靖", "玉溪",
            "贵阳", "遵义", "六盘水",
            "长春", "吉林",
            "哈尔滨", "齐齐哈尔", "大庆",
            "兰州", "天水",
            "呼和浩特", "包头", "鄂尔多斯",
            "乌鲁木齐", "克拉玛依",
            "拉萨", "西宁", "银川",
        ]
        for c in sorted(cities, key=lambda x: -len(x)):
            if c in title:
                return c
        return ""

    def _extract_province(self, title: str) -> str:
        provinces = [
            "广东", "广西", "福建", "海南", "浙江", "湖南", "安徽", "山东",
            "江苏", "四川", "湖北", "河南", "河北", "辽宁", "江西", "陕西",
            "山西", "云南", "贵州", "吉林", "黑龙江", "甘肃", "内蒙古",
            "新疆", "西藏", "青海", "宁夏",
        ]
        for p in sorted(provinces, key=lambda x: -len(x)):
            if p in title:
                return p
        for d in ["北京", "上海", "天津", "重庆"]:
            if d in title:
                return d
        return ""
