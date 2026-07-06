"""
从 zhaobiao.cn 爬取广东移动广告类招标数据
搜索条件：广东移动 广告 | 招标公告 | 2026-06-15 起
"""
import asyncio
import re
import sys
import os
from datetime import datetime, date
from playwright.async_api import async_playwright

# 搜索关键词
SEARCH_KEYWORD = "广东移动 广告"
# 起始日期
START_DATE = "2026-06-15"

# 结果输出文件
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "..", "output", "zhaobiao_gd_mobile_ads.json")


async def main():
    results = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()
        
        try:
            # 1. 打开首页
            print("📡 打开 zhaobiao.cn...")
            await page.goto("https://www.zhaobiao.cn", wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(2000)
            
            # 2. 搜索
            print(f"🔍 搜索: {SEARCH_KEYWORD}")
            search_input = page.locator('input[placeholder*="搜索"]').first
            await search_input.fill(SEARCH_KEYWORD)
            await page.wait_for_timeout(500)
            
            # 点击搜索按钮
            search_btn = page.locator('a:has-text("搜 索")').first
            await search_btn.click()
            await page.wait_for_timeout(3000)
            
            # 3. 勾选"招标公告"
            print("☑️ 筛选: 招标公告")
            try:
                zb_checkbox = page.locator('text=招标公告').first
                # 找到对应的checkbox
                zb_label = page.locator('label:has-text("招标公告")').first
                if await zb_label.count() > 0:
                    await zb_label.click()
                    await page.wait_for_timeout(2000)
            except Exception as e:
                print(f"   ⚠️ 招标公告筛选失败: {e}")
            
            # 4. 设置日期范围 (自定义时间)
            print(f"📅 设置日期: {START_DATE} 至今")
            try:
                # 点击"发布时间"展开
                time_header = page.locator('text=发布时间').first
                await time_header.click()
                await page.wait_for_timeout(1000)
                
                # 点击"自定义时间范围"
                custom_time = page.locator('text=自定义时间范围').first
                if await custom_time.count() > 0:
                    await custom_time.click()
                    await page.wait_for_timeout(1000)
                    
                    # 填入开始日期
                    start_inputs = page.locator('input[placeholder*="开始"]')
                    if await start_inputs.count() == 0:
                        start_inputs = page.locator('input[type="text"]').nth(0)
                    start_input = start_inputs.first
                    await start_input.fill(START_DATE)
                    await page.wait_for_timeout(500)
                    
                    # 确认按钮
                    confirm_btn = page.locator('button:has-text("确定"), a:has-text("确定")').first
                    if await confirm_btn.count() > 0:
                        await confirm_btn.click()
                        await page.wait_for_timeout(3000)
            except Exception as e:
                print(f"   ⚠️ 日期设置失败，使用默认最近3月: {e}")
            
            # 5. 逐页爬取结果
            page_num = 1
            while True:
                print(f"\n📄 第 {page_num} 页...")
                await page.wait_for_timeout(2000)
                
                # 提取当前页结果
                page_results = await extract_results(page)
                if not page_results:
                    print("   ⚠️ 本页无结果，停止翻页")
                    break
                
                print(f"   ✅ 提取 {len(page_results)} 条")
                results.extend(page_results)
                
                # 尝试翻页
                next_btn = page.locator('a:has-text("下一页"), a:has-text("›")').first
                if await next_btn.count() > 0 and await next_btn.is_enabled():
                    await next_btn.click()
                    page_num += 1
                    await page.wait_for_timeout(3000)
                else:
                    print("   🏁 已到最后一页")
                    break
                
                # 限制最多10页
                if page_num > 10:
                    print("   ⚠️ 已达最大页数限制(10页)")
                    break
            
            print(f"\n🎉 爬取完成！共 {len(results)} 条结果")
            
            # 6. 保存结果
            import json
            os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f"💾 已保存到: {OUTPUT_FILE}")
            
        except Exception as e:
            print(f"❌ 爬取出错: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()
    
    return results


async def extract_results(page):
    """从当前页面提取搜索结果"""
    items = []
    
    try:
        # 查找结果表格行
        rows = page.locator('table tr, .result-item, .list-item, [class*="item"]')
        count = await rows.count()
        
        for i in range(count):
            try:
                row = rows.nth(i)
                text = await row.inner_text()
                text = text.strip()
                
                # 跳过表头、空行
                if not text or len(text) < 10:
                    continue
                if '类型' in text and '标题' in text and '发布时间' in text:
                    continue
                
                # 提取链接
                links = await row.locator('a').all()
                url = ""
                title = ""
                for link in links:
                    href = await link.get_attribute('href')
                    link_text = (await link.inner_text()).strip()
                    if href and link_text and len(link_text) > 5:
                        url = href
                        title = link_text
                        if not url.startswith('http'):
                            url = f"https://s.zhaobiao.cn{url}" if url.startswith('/') else f"https://s.zhaobiao.cn/{url}"
                        break
                
                if not title:
                    continue
                
                # 解析行内容
                lines = [l.strip() for l in text.split('\n') if l.strip()]
                
                item = {
                    "title": title,
                    "source_url": url,
                    "raw_text": text,
                    "crawl_date": datetime.now().isoformat(),
                }
                
                # 尝试提取地点和时间
                for line in lines:
                    if re.match(r'\d{4}-\d{2}-\d{2}', line):
                        item["publish_date"] = line
                    elif line in ["广东", "广西", "湖南", "江西", "福建", "海南", "江苏", "浙江", "四川", "云南"]:
                        item["province"] = line
                
                if not any(existing["title"] == item["title"] for existing in items):
                    items.append(item)
                    
            except Exception:
                continue
    except Exception as e:
        print(f"   ⚠️ 提取结果出错: {e}")
    
    return items


if __name__ == "__main__":
    results = asyncio.run(main())
    print(f"\n总计: {len(results)} 条")
