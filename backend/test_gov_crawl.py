"""
测试：广东政府广告招标信息采集
通过 API POST /api/v1/announcements/fetch 触发爬虫
"""
import httpx
import time
import json

BASE = "http://localhost:8000"

def main():
    # 1. 触发政府来源采集 (ccgp + gd_zbtb + gd_ygp)
    print("=" * 60)
    print("  🧪 测试广东政府广告招标信息采集")
    print("=" * 60)

    # 方式1: 通过 API trigger (ccgp 政府来源)
    print("\n📡 [1] 触发 ccgp (中国政府采购网) 采集...")
    r = httpx.post(f"{BASE}/api/v1/announcements/fetch",
                   params={"adapter": "ccgp", "province": "广东"})
    result = r.json()
    print(f"    响应: {json.dumps(result, ensure_ascii=False, indent=2)}")

    task_id = result.get("task_id", "")
    if task_id:
        print(f"\n    ⏳ 等待采集完成 (task_id={task_id})...")
        for i in range(30):
            time.sleep(2)
            r2 = httpx.get(f"{BASE}/api/v1/announcements/fetch/status/{task_id}")
            status = r2.json()
            print(f"    [{i*2}s] progress={status.get('progress', 0)}%, status={status.get('status')}, msg={status.get('message', '')[:60]}")
            if status.get("status") in ("completed", "failed"):
                print(f"\n    ✅ 最终状态: {json.dumps(status, ensure_ascii=False, indent=2)}")
                break
    else:
        print("    ⚠️ 未返回 task_id，可能是同步完成")

    # 2. 检查结果
    print("\n📊 [2] 检查采集结果...")
    for src in ["ccgp", "gd_zbtb", "gd_ygp", "zhaobiao"]:
        r = httpx.get(f"{BASE}/api/v1/announcements", params={
            "page_size": 1, "data_source": src
        })
        total = r.json()["total"]
        print(f"    {src}: {total} 条")

    r = httpx.get(f"{BASE}/api/v1/announcements", params={"page_size": 1})
    print(f"    全部: {r.json()['total']} 条")

    print("\n✅ 测试完成!")


if __name__ == "__main__":
    main()
