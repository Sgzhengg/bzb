"""客情-项目自动关联提醒 — 集成测试"""
import httpx
import asyncio

BASE = "http://localhost:8000/api/v1"

async def test_all():
    print("=" * 60)
    print("客情-项目关联提醒 — 集成测试")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=10) as client:

        # ── 清理历史测试数据 ──
        print("🧹 清理历史测试数据")
        # 删除测试客情
        r = await client.get(f"{BASE}/relations?limit=100")
        if r.status_code == 200:
            for item in r.json().get("items", []):
                if item["contact_name"].startswith("关联测试_"):
                    await client.delete(f"{BASE}/relations/{item['id']}")
        # 删除测试公告的提醒
        import subprocess as sp
        sp.run([
            "docker", "exec", "bzb-postgres", "psql", "-U", "postgres", "-d", "biaozhongbao",
            "-c", "DELETE FROM project_relation_alerts WHERE announcement_id IN (SELECT id FROM announcements WHERE title LIKE '测试公告%')"
        ], capture_output=True)
        sp.run([
            "docker", "exec", "bzb-postgres", "psql", "-U", "postgres", "-d", "biaozhongbao",
            "-c", "DELETE FROM announcements WHERE title LIKE '测试公告%'"
        ], capture_output=True)
        print("  清理完成")

        # ── 准备：插入测试公告 + 客情数据 ──
        print("\n📌 准备测试数据")

        # 插入采购方（如已存在会因唯一约束失败，忽略）
        # 直接用已知的采购方 1

        # 插入客情记录
        r = await client.post(f"{BASE}/relations", json={
            "purchaser_id": 1, "contact_name": "关联测试_张三",
            "title": "采购总监", "phone": "13800000001",
            "rating": "S", "contact_method": "面谈",
            "last_contact_date": "2026-06-20",
            "contact_summary": "关系很好，经常合作",
        })
        assert r.status_code == 201, f"创建客情失败: {r.text}"
        rel_id = r.json()["id"]
        print(f"  ✅ 客情记录 #{rel_id}: 张三(S)")

        # 插入公告（通过原始SQL，因为没有announcements API）
        # 用 docker exec 插入
        import subprocess
        subprocess.run([
            "docker", "exec", "bzb-postgres", "psql", "-U", "postgres", "-d", "biaozhongbao",
            "-c",
            f"INSERT INTO announcements (title, purchaser_id, purchaser_level, procurement_method, project_category, announce_date, deadline, source_url) "
            f"VALUES ('测试公告-客情关联提醒', 1, '省公司', '公开招标', '媒介投放类', '2026-06-26', '2026-07-26 17:00:00', 'http://test') "
            f"ON CONFLICT DO NOTHING"
        ], capture_output=True)

        # 获取最新公告ID
        import subprocess as sp
        result = sp.run([
            "docker", "exec", "bzb-postgres", "psql", "-U", "postgres", "-d", "biaozhongbao",
            "-t", "-c", "SELECT id FROM announcements ORDER BY id DESC LIMIT 1"
        ], capture_output=True, text=True)
        ann_id = int(result.stdout.strip())
        print(f"  ✅ 公告 #{ann_id}: 测试公告-客情关联提醒")

        # ── 1. POST 触发检测 ──
        print("\n📌 1. POST /alerts/check/{id} 触发检测")
        r = await client.post(f"{BASE}/alerts/check/{ann_id}")
        assert r.status_code == 200, f"检测失败: {r.text}"
        data = r.json()
        assert data["created"] == True, "应创建提醒"
        assert data["count"] >= 1, f"至少1条提醒"
        print(f"  ✅ 创建 {data['count']} 条提醒: {data['message']}")

        # ── 2. 重复触发应跳过 ──
        print("\n📌 2. 重复检测 → 应跳过（已存在）")
        r = await client.post(f"{BASE}/alerts/check/{ann_id}")
        data = r.json()
        assert data["created"] == False, "重复检测不应再创建"
        print(f"  ✅ 跳过: {data['message']}")

        # ── 3. GET 提醒列表 ──
        print("\n📌 3. GET /alerts/announcement/{id}")
        r = await client.get(f"{BASE}/alerts/announcement/{ann_id}")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 1
        alert_item = data["items"][0]
        assert "张三" in alert_item["alert_reason"]
        assert "采购总监" in alert_item["alert_reason"]
        assert "S" in alert_item["alert_reason"]
        assert alert_item["is_read"] == False
        alert_id = alert_item["id"]
        print(f"  ✅ 提醒#{alert_id}: {alert_item['alert_reason'][:60]}...")

        # ── 4. 未读提醒查询 ──
        print("\n📌 4. GET /alerts/unread-count 未读数")
        r = await client.get(f"{BASE}/alerts/unread-count")
        assert r.status_code == 200
        data = r.json()
        print(f"  ✅ 未读提醒: {data['unread_count']} 条")

        # ── 5. 仅未读筛选 ──
        print("\n📌 5. GET /alerts/announcement/{id}?unread_only=true")
        r = await client.get(f"{BASE}/alerts/announcement/{ann_id}?unread_only=true")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 1
        print(f"  ✅ 未读筛选: {data['total']} 条")

        # ── 5a. 记录标记前未读数 ──
        r = await client.get(f"{BASE}/alerts/announcement/{ann_id}?unread_only=true")
        unread_before = r.json()["total"]
        print(f"  📎 标记前未读: {unread_before} 条")

        # ── 6. 标记单条已读 ──
        print("\n📌 6. PUT /alerts/{id}/read 标记已读")
        r = await client.put(f"{BASE}/alerts/{alert_id}/read")
        assert r.status_code == 200
        print(f"  ✅ {r.json()['message']}")

        # ── 7. 验证已读 ──
        r = await client.get(f"{BASE}/alerts/announcement/{ann_id}?unread_only=true")
        data = r.json()
        assert data["total"] == unread_before - 1, f"标记已读后应减少1: {unread_before}→{data['total']}"
        print(f"  ✅ 已读后未读: {unread_before}→{data['total']}")

        # ── 8. 批量标记已读 ──
        # 先创建另一条提醒，再批量标记
        r = await client.post(f"{BASE}/relations", json={
            "purchaser_id": 1, "contact_name": "关联测试_李四",
            "rating": "A", "contact_method": "电话",
            "last_contact_date": "2026-06-15",
        })
        assert r.status_code == 201
        rel_id2 = r.json()["id"]

        r = await client.post(f"{BASE}/alerts/check/{ann_id}")
        assert r.json()["created"] == True

        r = await client.put(f"{BASE}/alerts/announcement/{ann_id}/read")
        assert r.status_code == 200
        data = r.json()
        assert data["updated_count"] >= 1, f"批量标记至少1条: {data['updated_count']}"
        print(f"  ✅ 批量标记已读: {data['updated_count']} 条")

        # ── 9. 错误处理 ──
        print("\n📌 9. 错误处理")
        r = await client.post(f"{BASE}/alerts/check/99999")
        assert r.status_code == 404
        print(f"  ✅ 公告不存在→404")

        # ── 10. 批量处理 ──
        print("\n📌 10. POST /alerts/batch 批量处理")
        r = await client.post(f"{BASE}/alerts/batch?limit=10")
        assert r.status_code == 200
        data = r.json()
        print(f"  ✅ 批量: checked={data['total_checked']}, "
              f"created={data['alerts_created']}, skipped={data['skipped']}")

        # ── 清理 ──
        print("\n🧹 清理测试数据")
        await client.delete(f"{BASE}/relations/{rel_id}")
        await client.delete(f"{BASE}/relations/{rel_id2}")

    print("\n" + "=" * 60)
    print("🎉 全部 10 项集成测试通过！")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_all())
