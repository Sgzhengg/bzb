"""对全部公告执行6维评分并入库"""
import sys, os, json, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.services.opportunity_scorer import WEIGHTS, _probability_label, OpportunityScore, ScoreDetail

import psycopg2
from collections import Counter

conn = psycopg2.connect(host='localhost', user='postgres', password='postgres', dbname='biaozhongbao')
cur = conn.cursor()

# 1. Load all announcements
cur.execute('SELECT id, title, purchaser_id, purchaser_level, procurement_method, budget, project_category, province, city FROM announcements')
announcements = cur.fetchall()

# 2. Load user preferences
cur.execute('SELECT preferred_categories, min_budget, min_score FROM user_preferences WHERE id=1')
pref = cur.fetchone()
preferred_categories = []
if pref and pref[0]:
    try: preferred_categories = json.loads(pref[0])
    except: pass

# 3. Load client relations (for 客情关系维度)
cur.execute('SELECT purchaser_id, rating FROM client_relations')
relations = cur.fetchall()
relation_map = {}
RATING_SCORE = {'S': 100, 'A': 80, 'B': 60, 'C': 40, 'D': 20}
for pid, rating in relations:
    score = RATING_SCORE.get(rating, 0)
    if pid not in relation_map or score > relation_map[pid]:
        relation_map[pid] = score

# 4. Budget stats for 预算健康度
cur.execute('SELECT project_category, AVG(budget), STDDEV(budget) FROM announcements WHERE budget IS NOT NULL GROUP BY project_category')
budget_stats = {}
for row in cur.fetchall():
    avg_val = float(row[1]) if row[1] else 0
    std_val = float(row[2]) if row[2] else avg_val * 0.5
    budget_stats[row[0]] = (avg_val, std_val)
global_avg_budget = sum(v[0] for v in budget_stats.values()) / max(len(budget_stats), 1)

print(f'Total announcements: {len(announcements)}')
print(f'Preferred categories: {preferred_categories}')
print(f'Client relations: {len(relations)}')
print(f'Budget categories: {len(budget_stats)}')

# 5. Score each announcement
scored = 0
for aid, title, pid, plevel, pmethod, budget, pcat, province, city in announcements:
    # 5a. 采购方式公平性 (20%)
    method_score_map = {'公开招标': 100, '公开询比': 80, '竞争性谈判': 50, '单一来源': 0}
    procurement_fairness = method_score_map.get(pmethod, 60)
    
    # 5b. HHI 集中度 (20%) — 无历史数据，用默认值
    hhi_concentration = 60.0  # 中性默认
    
    # 5c. 项目类型匹配度 (20%)
    if not preferred_categories:
        category_match = 60.0
    elif pcat in preferred_categories:
        category_match = 100.0
    else:
        category_match = 50.0
    
    # 5d. 预算健康度 (15%)
    if budget and pcat in budget_stats:
        avg, std = budget_stats[pcat]
        z = abs(float(budget) - avg) / max(std, 1)
        if z < 0.5: budget_health = 100.0
        elif z < 1: budget_health = 85.0
        elif z < 1.5: budget_health = 70.0
        elif z < 2: budget_health = 50.0
        else: budget_health = 30.0
    else:
        budget_health = 60.0  # 无预算数据，中性
    
    # 5e. 在位者优势 (15%) — 无历史数据，用默认值
    incumbent_advantage = 50.0  # 中性默认
    
    # 5f. 客情关系强度 (10%)
    client_relation = relation_map.get(pid, 0)
    
    # 加权总分
    total = (
        procurement_fairness * WEIGHTS['procurement_fairness'] +
        hhi_concentration * WEIGHTS['hhi_concentration'] +
        category_match * WEIGHTS['category_match'] +
        budget_health * WEIGHTS['budget_health'] +
        incumbent_advantage * WEIGHTS['incumbent_advantage'] +
        client_relation * WEIGHTS['client_relation']
    )
    total = round(total, 1)
    prob_label = _probability_label(total)
    
    # 更新数据库
    cur.execute('''UPDATE announcements SET total_score=%s, probability_label=%s WHERE id=%s''',
               (total, prob_label, aid))
    scored += 1

conn.commit()

# 6. Stats
cur.execute('SELECT COUNT(*), AVG(total_score), MIN(total_score), MAX(total_score) FROM announcements WHERE total_score IS NOT NULL')
count, avg, mn, mx = cur.fetchone()
print(f'\n=== Scoring Complete ===')
print(f'Scored: {count} announcements')
print(f'Average: {avg:.1f}, Range: {mn:.0f}-{mx:.0f}')

cur.execute("SELECT probability_label, COUNT(*) FROM announcements WHERE probability_label IS NOT NULL GROUP BY probability_label ORDER BY 2 DESC")
for label, cnt in cur.fetchall():
    print(f'  {label}: {cnt}')

cur.close()
conn.close()
print('Done!')
