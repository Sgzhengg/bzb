"""
中国移动采购与招标网 (b2b.10086.cn) 爬虫适配器

数据源:
  - 列表: queryList JSON API
  - 详情: queryDetail JSON API → PDF base64 解码

字段提取:
  - title: API 返回
  - province/city: 正则从标题提取 + API regionName
  - budget/registration_fee/deposit: LLM 从 PDF 正文提取
  - project_category: LLM 分类
  - original_content: PDF 解码全文
  - source_url: viewNoticeContent.html 格式
"""

import re
import base64
import ssl
from typing import List, Dict, Optional, Tuple

import httpx
from bs4 import BeautifulSoup

from .base_adapter import BaseAdapter


class B2b10086Adapter(BaseAdapter):
    """中国移动采购与招标网 (b2b.10086.cn) 适配器"""

    BASE_URL = "https://b2b.10086.cn"
    LIST_API = "https://b2b.10086.cn/api-b2b/api-sync-es/white_list_api/b2b/publish/queryList"
    DETAIL_API = "https://b2b.10086.cn/api-b2b/api-sync-es/white_list_api/b2b/publish/queryDetail"

    PUBLISH_TYPES = ["PROCUREMENT", "VENDOR", "PURCHASE_SERVICE"]

    def __init__(self, config: dict = None):
        default_config = {
            "name": "中国移动采购与招标网",
            "base_url": self.BASE_URL,
            "min_delay": 2.0,
            "max_delay": 4.0,
            "max_retries": 2,
            "timeout": 30,
            "max_pages": 3,
            "search_keyword": "移动 广告 宣传",
        }
        if config:
            default_config.update(config)
        super().__init__(default_config)

        self._client = None
        self._seen_ids = set()
        self._current_item = None  # 当前正在处理的 b2b item（传递 uuid 用）
        self.search_keywords = [
            # 精准广告关键词（优先匹配真实广告类项目）
            "广告设计", "品牌推广", "活动策划", "新媒体运营",
            "媒介投放", "视频制作", "创意设计", "品牌宣传",
            "广告代理", "营销策划", "内容制作", "直播运营",
            "广告物料", "宣传品制作", "喷绘制作", "展会搭建",
            "路演活动", "短视频", "H5制作",
            # 广义兜底
            "广告", "宣传", "活动", "品牌", "新媒体", "视频", "物料", "设计",
        ]

    def get_source_name(self) -> str:
        return "b2b_10086"

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            ctx.options |= 0x4  # SSL_OP_LEGACY_SERVER_CONNECT

            self._client = httpx.Client(
                transport=httpx.HTTPTransport(verify=ctx),
                timeout=httpx.Timeout(self.timeout),
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": self._next_ua(),
                },
            )
        return self._client

    # ── 列表页 ──

    def fetch_list(self, page: int = 1) -> str:
        """通过 JSON API 搜索，返回 JSON 字符串。"""
        keywords = self.search_keywords
        client = self._get_client()

        all_items = []
        seen = set()

        for kw in keywords:
            for ptype in ["PROCUREMENT", "PURCHASE_SERVICE"]:
                try:
                    self._random_delay()
                    resp = client.post(
                        self.LIST_API,
                        json={
                            "name": kw,
                            "publishType": ptype,
                            "size": 20,
                            "current": page,
                            "sfactApplColumn5": "PC",
                        },
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        items = data.get("data", {}).get("content", [])
                        for item in items:
                            pid = str(item.get("id", ""))
                            if pid and pid not in seen:
                                seen.add(pid)
                                item["_publishType"] = ptype
                                all_items.append(item)
                except Exception as e:
                    self.logger.warning(f"搜索失败 '{kw}' ({ptype}): {e}")

        import json as _json
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
        province_matched = 0
        for item in items:
            item_id = str(item.get("id", ""))
            title = item.get("name", "")

            if not item_id or not title:
                continue
            if item_id in self._seen_ids:
                continue
            self._seen_ids.add(item_id)

            if not self._is_mobile(title):
                continue

            # 跳过中标公示
            if self._is_winning_announcement(title):
                self.logger.debug(f"  ⏭️ 跳过中标公示: {title[:60]}")
                continue

            # 省份过滤（如果指定了省份）
            if province and not self._match_province(title, province):
                province_matched += 1
                continue

            pid = item.get("id", "")
            puid = item.get("uuid", "")
            one_type = item.get("publishOneType", "PROCUREMENT")
            # 使用 SPA 路由格式，可直接在浏览器打开公告详情页
            # publishType 在 URL 中固定为 PROCUREMENT，子类型由 publishOneType 区分
            detail_url = (
                f"{self.BASE_URL}/#/noticeDetail"
                f"?publishId={pid}"
                f"&publishUuid={puid}"
                f"&publishType=PROCUREMENT"
                f"&publishOneType={one_type}"
            )

            results.append({
                "title": title,
                "publish_date": item.get("publishDate", ""),
                "detail_url": detail_url,
                "notice_type": item.get("publishOneType", "PROCUREMENT"),
                "_b2b_item": item,
            })

        self.logger.info(f"b2b.10086.cn 列表解析: {len(results)} 条")
        return results

    def _is_mobile(self, title: str) -> bool:
        """判断是否中国移动相关公告。"""
        keywords = [
            "中国移动", "广东移动", "广西移动", "福建移动", "海南移动",
            "浙江移动", "湖南移动", "安徽移动", "山东移动", "江苏移动",
            "四川移动", "湖北移动", "河南移动", "河北移动", "辽宁移动",
            "江西移动", "陕西移动", "山西移动", "云南移动", "贵州移动",
            "吉林移动", "黑龙江", "甘肃移动", "内蒙古移动",
            "新疆移动", "西藏移动", "青海移动", "宁夏移动",
            "北京移动", "上海移动", "天津移动", "重庆移动",
            "移动通信集团",
        ]
        return any(kw in title for kw in keywords)

    def _is_winning_announcement(self, title: str) -> bool:
        """判断是否为中标公示（中选/中标候选人/结果公示），应入 awards 表而非 announcements。"""
        patterns = [
            "中选候选人", "中选结果", "中选人",
            "中标候选人", "中标结果", "中标人",
            "成交候选人", "成交结果",
            "_中选", "_中标", "_成交",
        ]
        return any(p in title for p in patterns)

    def _match_province(self, title: str, province: str) -> bool:
        """检查标题是否匹配指定省份。"""
        province_map = {
            "广东": ["广东", "广州", "深圳", "东莞", "佛山", "珠海", "惠州", "中山", "江门", "汕头", "湛江", "茂名", "肇庆", "梅州", "汕尾", "河源", "阳江", "清远", "韶关", "潮州", "揭阳", "云浮"],
            "广西": ["广西", "南宁", "柳州", "桂林", "玉林", "梧州", "北海", "贵港", "钦州", "百色", "河池", "贺州", "来宾", "崇左", "防城港"],
            "福建": ["福建", "福州", "厦门", "泉州", "漳州", "龙岩", "三明", "南平", "莆田", "宁德"],
            "海南": ["海南", "海口", "三亚", "儋州"],
            "浙江": ["浙江", "杭州", "宁波", "温州", "嘉兴", "湖州", "绍兴", "金华", "衢州", "舟山", "台州", "丽水"],
            "湖南": ["湖南", "长沙", "株洲", "湘潭", "衡阳", "邵阳", "岳阳", "常德", "张家界", "益阳", "郴州", "永州", "怀化", "娄底"],
            "安徽": ["安徽", "合肥", "芜湖", "蚌埠", "淮南", "马鞍山", "淮北", "铜陵", "安庆", "黄山", "滁州", "阜阳", "宿州", "六安", "亳州", "池州", "宣城"],
            "山东": ["山东", "济南", "青岛", "淄博", "枣庄", "东营", "烟台", "潍坊", "济宁", "泰安", "威海", "日照", "临沂", "德州", "聊城", "滨州", "菏泽"],
            "江苏": ["江苏", "南京", "苏州", "无锡", "常州", "南通", "扬州", "镇江", "泰州", "盐城", "徐州", "淮安", "连云港", "宿迁"],
            "四川": ["四川", "成都", "绵阳", "德阳", "宜宾", "南充", "泸州", "达州", "乐山"],
            "湖北": ["湖北", "武汉", "宜昌", "襄阳", "荆州", "黄冈", "孝感", "十堰", "荆门"],
            "河南": ["河南", "郑州", "洛阳", "南阳", "许昌", "周口", "新乡", "商丘"],
            "北京": ["北京", "东城", "西城", "朝阳", "海淀"],
            "上海": ["上海", "浦东", "黄浦", "徐汇", "静安"],
            "重庆": ["重庆", "渝中", "江北", "南岸", "渝北"],
            "天津": ["天津", "和平", "河东", "河西", "南开", "滨海"],
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
        """通过 queryDetail API 获取 PDF 内容。支持新旧两种 URL 格式。"""
        notice_id = ""
        # 新格式: #/noticeDetail?publishId=xxx
        m = re.search(r"publishId=(\d+)", url)
        if m:
            notice_id = m.group(1)
        # 旧格式: viewNoticeContent.html?noticeBean.id=xxx
        if not notice_id:
            m = re.search(r"noticeBean\.id=(\d+)", url)
            if m:
                notice_id = m.group(1)

        if not notice_id:
            return "", None

        # 从 _current_item 获取 uuid 和 publishType
        puid = ""
        ptype = "PROCUREMENT"
        if hasattr(self, "_current_item") and self._current_item:
            puid = self._current_item.get("uuid", "")
            ptype = self._current_item.get("_publishType", "PROCUREMENT")

        client = self._get_client()
        self._random_delay()

        try:
            body = {
                "publishId": notice_id,
                "publishType": ptype,
                "sfactApplColumn5": "PC",
            }
            if puid:
                body["publishUuid"] = puid

            resp = client.post(self.DETAIL_API, json=body)
            if resp.status_code == 200:
                data = resp.json()
                detail = data.get("data", {})
                notice_content = detail.get("noticeContent", "")

                if notice_content:
                    try:
                        pdf_bytes = base64.b64decode(notice_content)
                        return detail.get("name", ""), pdf_bytes
                    except Exception:
                        pass

                return detail.get("name", "") or "", None

        except Exception as e:
            self.logger.warning(f"详情获取失败 {notice_id}: {e}")

        return "", None

    def parse_detail(self, html: str, pdf_bytes: Optional[bytes] = None) -> Dict:
        """
        解析详情页/PDF，提取全部字段。

        html 参数实际为公告标题（由 fetch_detail 传入）
        pdf_bytes 为解码后的 PDF 内容
        """
        title = html or ""
        content_text = ""

        if pdf_bytes:
            try:
                import fitz
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                pages = []
                for pn in range(len(doc)):
                    t = doc[pn].get_text()
                    if t.strip():
                        pages.append(t)
                doc.close()
                content_text = "\n".join(pages)
                self.logger.info(f"  PDF 解码: {len(content_text)} 字符")
            except Exception as e:
                self.logger.warning(f"  PDF 解码失败: {e}")

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

    # ── 主流程（覆盖基类以传递 uuid） ──

    def run(self, save_to_db: bool = True, **kwargs) -> List[Dict]:
        """执行完整采集流程，在抓取详情前设置 _current_item 用于传递 uuid。

        Args:
            save_to_db: 是否入库
            **kwargs: 支持 province 参数进行省份过滤
        """
        province_filter = kwargs.get("province", "")
        all_results = []
        seen_urls = set()

        # 重置去重集合，确保每次采集独立
        self._seen_ids.clear()
        existing_titles = self._load_existing_titles()  # 加载已有标题，跳过重复

        self.logger.info(f"===== {self.name} 开始采集 (省份={province_filter or '不限'}) =====")

        # 如果指定了省份，将省份名加入搜索关键词
        if province_filter:
            # 省份关键词放前面，确保优先搜索该省相关公告
            province_keywords = [
                f"{province_filter}移动",
                province_filter,
            ]
            self.search_keywords = province_keywords + self.search_keywords

        # 计算总工作量（用于进度估算）
        total_work = self.max_pages * len(self.search_keywords) * 2  # 页数 × 关键词数 × 2种类型
        current_work = 0

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

                    detail_url = item.get("detail_url", "")
                    if not detail_url or detail_url in seen_urls:
                        continue
                    seen_urls.add(detail_url)

                    # 设置当前 b2b item（用于 fetch_detail 获取 uuid）
                    self._current_item = item.get("_b2b_item", {})

                    # 跳过数据库中已存在的记录
                    title_check = item.get("title", "")
                    if title_check in existing_titles:
                        self.logger.debug(f"  ⏭️ 已存在，跳过: {title_check[:60]}")
                        continue

                    self._report_progress(item_progress, f"处理第 {page} 页第 {i+1}/{len(items)} 个公告...")

                    try:
                        html_detail, pdf_bytes = self.fetch_detail(detail_url)
                        parsed = self.parse_detail(html_detail, pdf_bytes)
                        parsed["source_url"] = detail_url
                        parsed["notice_type"] = item.get("notice_type", parsed.get("notice_type", ""))

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
        m = re.search(r"(中国移动通信集团[^，。；\n]{0,30}(?:有限公司|分公司))", title + content)
        return m.group(1) if m else ""

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
            "张家界", "益阳", "郴州", "永州", "怀化", "娄底",
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
        # 检查直辖市
        for d in ["北京", "上海", "天津", "重庆"]:
            if d in title:
                return d
        return ""
