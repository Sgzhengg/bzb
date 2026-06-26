"""客情管理 API — 集成测试脚本"""
import httpx
import asyncio
import json

BASE = "http://localhost:8000/api/v1/relations"

async def test_all():
    print("=" * 60)
    print("客情管理 CRUD API — 集成测试")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=10) as client:
        # ── 清理历史测试数据 ──
        # 获取所有数据并删除 name 匹配的用户
        r = await client.get(BASE + "?limit=100")
        if r.status_code == 200:
            existing = r.json().get("items", [])
            test_names = {"张三", "李四", "王五", "赵六"}
            for item in existing:
                if item["contact_name"] in test_names:
                    await client.delete(f"{BASE}/{item['id']}")
            print("🧹 清理历史测试数据完成")

        # ── 1. POST 创建 ──
        print("\n📌 1. POST 创建客情记录")
        payloads = [
            {"purchaser_id": 1, "contact_name": "张三", "title": "采购经理",
             "phone": "13800138001", "email": "zhangsan@test.com",
             "rating": "S", "contact_method": "面谈",
             "last_contact_date": "2026-06-20", "next_followup_date": "2026-06-26",
             "contact_summary": "讨论了下半年广告投放计划"},
            {"purchaser_id": 1, "contact_name": "李四", "title": "市场主管",
             "phone": "13800138002", "rating": "A", "contact_method": "微信",
             "last_contact_date": "2026-06-15", "next_followup_date": "2026-06-26"},
            {"purchaser_id": 2, "contact_name": "王五", "title": "品牌经理",
             "phone": "13800138003", "rating": "B", "contact_method": "电话",
             "last_contact_date": "2026-06-10", "next_followup_date": "2026-06-26"},
            {"purchaser_id": 3, "contact_name": "赵六", "title": "营销总监",
             "rating": "C", "last_contact_date": "2026-05-01"},
        ]
        ids = []
        for i, p in enumerate(payloads):
            r = await client.post(BASE + "", json=p)
            assert r.status_code == 201, f"创建#{i}失败: {r.status_code} {r.text}"
            data = r.json()
            assert data["contact_name"] == p["contact_name"]
            ids.append(data["id"])
            print(f"  ✅ 创建 #{ids[-1]}: {p['contact_name']} (rating={p['rating']})")
        print(f"  创建 {len(ids)} 条成功")

        # ── 2. GET 列表（默认排序） ──
        print("\n📌 2. GET 客情列表")
        r = await client.get(BASE + "?limit=10")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 4
        items = data["items"]
        # 验证排序：S > A > B > C
        ratings = [i["rating"] for i in items]
        assert ratings == sorted(ratings, key=lambda x: {"S":0,"A":1,"B":2,"C":3,"D":4}[x]), \
            f"排序错误: {ratings}"
        print(f"  ✅ 总数={data['total']}, 排序正确: {ratings}")

        # ── 3. GET 按采购方筛选 ──
        print("\n📌 3. GET 按采购方筛选")
        r = await client.get(BASE + "?purchaser_id=1")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 2
        print(f"  ✅ 采购方1有{data['total']}条记录")

        # ── 4. GET 按评级筛选 ──
        print("\n📌 4. GET 按评级筛选")
        r = await client.get(BASE + "?rating=S")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 1
        assert data["items"][0]["rating"] == "S"
        print(f"  ✅ S级记录={data['total']}条")

        # ── 5. GET 单条详情 ──
        print("\n📌 5. GET 单条详情")
        r = await client.get(f"{BASE}/{ids[0]}")
        assert r.status_code == 200
        data = r.json()
        assert data["contact_name"] == "张三"
        assert data["rating"] == "S"
        assert data["email"] == "zhangsan@test.com"
        print(f"  ✅ 详情: {data['contact_name']} {data['title']}")

        # ── 6. PUT 更新 ──
        print("\n📌 6. PUT 更新客情记录")
        r = await client.put(f"{BASE}/{ids[3]}", json={"rating": "B", "phone": "13900139000"})
        assert r.status_code == 200
        data = r.json()
        assert data["rating"] == "B"
        assert data["phone"] == "13900139000"
        print(f"  ✅ 更新 #{ids[3]}: rating C→B, 添加电话")

        # ── 7. GET 按采购方获取 ──
        print("\n📌 7. GET /purchaser/{id}")
        r = await client.get(f"{BASE}/purchaser/1")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 2
        ratings = [i["rating"] for i in data]
        assert ratings == ["S", "A"]
        print(f"  ✅ 采购方1: {len(data)}条, S在A前")

        # ── 8. GET 今日提醒 ──
        print("\n📌 8. GET /reminders 今日提醒")
        r = await client.get(f"{BASE}/reminders")
        assert r.status_code == 200
        data = r.json()
        # 前3条 next_followup_date = 2026-06-26 (today)
        assert len(data) == 3  # 3条next_followup_date = today
        assert all(d["next_followup_date"] == "2026-06-26" for d in data)
        print(f"  ✅ 今日提醒: {len(data)}条")

        # ── 9. DELETE 删除 ──
        print("\n📌 9. DELETE 删除客情记录")
        r = await client.delete(f"{BASE}/{ids[0]}")
        assert r.status_code == 200
        data = r.json()
        assert "删除成功" in data["message"]
        print(f"  ✅ 删除 #{ids[0]} 成功")

        # 验证已删除
        r = await client.get(f"{BASE}/{ids[0]}")
        assert r.status_code == 404
        print(f"  ✅ 确认已删除 (404)")

        # ── 10. 错误处理 ──
        print("\n📌 10. 错误处理")

        # 404
        r = await client.get(f"{BASE}/99999")
        assert r.status_code == 404
        print(f"  ✅ 不存在记录→404")

        # 422 校验失败
        r = await client.post(BASE + "", json={"purchaser_id": 0})
        assert r.status_code == 422
        print(f"  ✅ purchaser_id=0→422")

        r = await client.post(BASE + "", json={"purchaser_id": 1, "contact_name": ""})
        assert r.status_code == 422
        print(f"  ✅ contact_name空→422")

        # 采购方不存在
        r = await client.post(BASE + "", json={"purchaser_id": 99999, "contact_name": "测试"})
        assert r.status_code == 404
        print(f"  ✅ 采购方不存在→404")

        # 清理：删除剩余测试数据
        for rid in ids[1:]:
            await client.delete(f"{BASE}/{rid}")

    print("\n" + "=" * 60)
    print("🎉 全部 10 项集成测试通过！")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_all())
