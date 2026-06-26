-- 测试数据插入脚本
INSERT INTO purchasers (name, level, region, hhi_score, sme_win_rate) VALUES
    ('中国移动通信集团广东有限公司', '省公司', '广州', 1200.5, 35.50),
    ('中国移动通信集团广东有限公司广州分公司', '地市公司', '广州', 980.3, 42.00),
    ('中国移动通信集团广东有限公司东莞分公司', '地市公司', '东莞', 850.0, 28.00);

INSERT INTO announcements (title, purchaser_id, purchaser_level, procurement_method, budget, project_category, announce_date, deadline, qualification_requirements, score_weight, source_url)
VALUES (
    '广东移动2024年度品牌传播策划服务项目',
    1,
    '省公司',
    '公开招标',
    500.00,
    '品牌策略',
    '2024-06-01',
    '2024-07-15 17:00:00',
    '投标人须具有独立法人资格，注册资金不低于1000万元，近三年具有同类项目经验',
    '{"tech": 0.40, "biz": 0.30, "price": 0.30}',
    'https://b2b.10086.cn/bidding/xxx'
);

INSERT INTO client_relations (purchaser_id, contact_name, title, phone, email, last_contact_date, contact_method, contact_summary, rating, next_followup_date)
VALUES (1, '张三', '采购经理', '13800138000', 'zhangsan@example.com', '2024-06-20', '面谈', '讨论了广告投放策略需求', 'A', '2024-07-01');

INSERT INTO project_relation_alerts (announcement_id, relation_id, alert_reason) VALUES (1, 1, '有A级客情关系，建议优先跟进');

-- 验证数据
SELECT 'purchasers' as tbl, count(*) FROM purchasers
UNION ALL SELECT 'announcements', count(*) FROM announcements
UNION ALL SELECT 'client_relations', count(*) FROM client_relations
UNION ALL SELECT 'project_relation_alerts', count(*) FROM project_relation_alerts;
