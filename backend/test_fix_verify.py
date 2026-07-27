"""测试修复后的 classify_and_extract 函数"""
import sys
sys.path.insert(0, 'd:/bzb/backend')

from app.services.llm_classifier import classify_and_extract, _parse_unified_response

# 模拟 LLM 返回 is_advertising 的 JSON
llm_response = '''{
  "is_advertising": true,
  "budget": 462.54,
  "registration_fee": 0,
  "deposit": null,
  "deadline": "2026-07-20",
  "bid_date": "2026-07-29",
  "procurement_method": "公开询比",
  "category": "视频内容制作",
  "reason": "视频制作服务属于内容制作类"
}'''

print("=== 测试 _parse_unified_response 兼容 is_advertising ===")
result = _parse_unified_response(llm_response)
print(f"is_ad: {result['is_ad']}")
print(f"deadline: {result['deadline']}")
print(f"bid_date: {result['bid_date']}")
print(f"budget: {result['budget']}")
print(f"category: {result['category']}")
print()

# 验证修复结果
assert result['is_ad'] == True, f"FAIL: is_ad should be True, got {result['is_ad']}"
assert result['deadline'] == '2026-07-20', f"FAIL: deadline wrong: {result['deadline']}"
assert result['bid_date'] == '2026-07-29', f"FAIL: bid_date wrong: {result['bid_date']}"
print("✅ 所有断言通过！修复生效。")
