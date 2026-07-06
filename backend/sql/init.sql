-- ============================================================
-- 标中宝 V1 — PostgreSQL 数据库建表脚本
-- 广东移动广告招标情报系统
-- ============================================================

-- 清理已有表（开发环境使用，生产环境请移除）
DROP TABLE IF EXISTS project_relation_alerts CASCADE;
DROP TABLE IF EXISTS client_relations CASCADE;
DROP TABLE IF EXISTS historical_awards CASCADE;
DROP TABLE IF EXISTS announcements CASCADE;
DROP TABLE IF EXISTS purchasers CASCADE;

-- ============================================================
-- 1. 采购方表
-- ============================================================
CREATE TABLE purchasers (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(200)    NOT NULL,                     -- 采购方名称
    level           VARCHAR(20)     NOT NULL DEFAULT '地市公司',   -- 层级：省公司 / 地市公司
    region          VARCHAR(50)     NOT NULL,                     -- 地区：广州 / 东莞 / 佛山 等
    hhi_score       NUMERIC(6,1)    DEFAULT 0,                    -- HHI集中度指数
    sme_win_rate    NUMERIC(5,2)    DEFAULT 0,                    -- 中小公司中标占比（%）
    created_at      TIMESTAMP       NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP       NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  purchasers              IS '采购方信息表';
COMMENT ON COLUMN purchasers.name         IS '采购方名称（如：中国移动通信集团广东有限公司广州分公司）';
COMMENT ON COLUMN purchasers.level        IS '采购方层级：省公司 / 地市公司';
COMMENT ON COLUMN purchasers.region       IS '所属地区：广州 / 东莞 / 佛山 / 深圳 等';
COMMENT ON COLUMN purchasers.hhi_score    IS 'HHI市场集中度指数，数值越大集中度越高';
COMMENT ON COLUMN purchasers.sme_win_rate IS '中小公司中标占比，单位%';

CREATE INDEX idx_purchasers_level  ON purchasers (level);
CREATE INDEX idx_purchasers_region ON purchasers (region);


-- ============================================================
-- 2. 招标公告表
-- ============================================================
CREATE TABLE announcements (
    id                          SERIAL PRIMARY KEY,
    title                       VARCHAR(500)    NOT NULL,                     -- 项目名称
    purchaser_id                INTEGER         NOT NULL,                     -- 采购方ID
    purchaser_level             VARCHAR(50)     NOT NULL,                     -- 采购方层级
    procurement_method          VARCHAR(30)     NOT NULL DEFAULT '公开招标',   -- 采购方式
    budget                      NUMERIC(12,2)   DEFAULT 0,                    -- 预算金额（万元）
    project_category            VARCHAR(30)     NOT NULL,                     -- 项目类别
    announce_date               DATE            NOT NULL,                     -- 公告发布时间
    deadline                    TIMESTAMP       NOT NULL,                     -- 投标截止时间
    qualification_requirements  TEXT,                                         -- 资格要求
    score_weight                JSONB,                                        -- 评分权重（JSON）
    source_url                  VARCHAR(1000),                                -- 原文链接
    created_at                  TIMESTAMP       NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMP       NOT NULL DEFAULT NOW(),

    -- 外键约束
    CONSTRAINT fk_announcements_purchaser
        FOREIGN KEY (purchaser_id) REFERENCES purchasers (id)
        ON DELETE RESTRICT ON UPDATE CASCADE
);

COMMENT ON TABLE  announcements                            IS '招标公告信息表';
COMMENT ON COLUMN announcements.title                      IS '招标项目名称';
COMMENT ON COLUMN announcements.purchaser_id               IS '采购方ID，关联 purchasers 表';
COMMENT ON COLUMN announcements.purchaser_level            IS '采购方层级：省公司 / 广州分公司 / 东莞分公司 / 佛山分公司 等';
COMMENT ON COLUMN announcements.procurement_method         IS '采购方式：公开招标 / 公开询比 / 竞争性谈判 / 单一来源';
COMMENT ON COLUMN announcements.budget                    IS '预算金额，单位：万元';
COMMENT ON COLUMN announcements.project_category           IS '项目类别：品牌策略 / 创意设计 / 媒介投放 / 活动执行 / 内容制作 / 新媒体运营';
COMMENT ON COLUMN announcements.announce_date              IS '公告发布日期';
COMMENT ON COLUMN announcements.deadline                   IS '投标截止日期时间';
COMMENT ON COLUMN announcements.qualification_requirements IS '投标资格要求详细描述';
COMMENT ON COLUMN announcements.score_weight               IS '评分权重，JSON格式，如：{"tech":0.4,"biz":0.3,"price":0.3}';
COMMENT ON COLUMN announcements.source_url                 IS '招标公告原始链接';

-- 核心联合索引：按采购方 + 发布时间查询
CREATE INDEX idx_announcements_purchaser_date
    ON announcements (purchaser_id, announce_date DESC);

-- 按发布时间排序
CREATE INDEX idx_announcements_date
    ON announcements (announce_date DESC);

-- 按项目类别筛选
CREATE INDEX idx_announcements_category
    ON announcements (project_category);

-- 按采购方式筛选
CREATE INDEX idx_announcements_method
    ON announcements (procurement_method);

-- 按采购方层级筛选
CREATE INDEX idx_announcements_level
    ON announcements (purchaser_level);

-- 预算范围查询（配合 ORDER 或 WHERE 使用）
CREATE INDEX idx_announcements_budget
    ON announcements (budget);

-- JSONB 索引（如需按评分权重中的技术分查询）
CREATE INDEX idx_announcements_score_weight
    ON announcements USING GIN (score_weight);


-- ============================================================
-- 3. 历史中标表
-- ============================================================
CREATE TABLE historical_awards (
    id                  SERIAL PRIMARY KEY,
    project_name        VARCHAR(500)    NOT NULL,                     -- 项目名称
    purchaser_id        INTEGER         NOT NULL,                     -- 采购方ID
    winner_name         VARCHAR(300)    NOT NULL,                     -- 中标方名称
    winner_type         VARCHAR(30)     NOT NULL,                     -- 中标方类型
    bid_amount          NUMERIC(12,2)   NOT NULL,                     -- 中标金额（万元）
    budget_amount       NUMERIC(12,2)   DEFAULT 0,                    -- 招标预算（万元）
    discount_rate       NUMERIC(6,2)    DEFAULT 0,                    -- 折扣率（%）
    project_category    VARCHAR(30)     NOT NULL,                     -- 项目类别
    bid_open_date       DATE            NOT NULL,                     -- 开标日期
    contract_start      DATE,                                         -- 合同开始日期
    contract_end        DATE,                                         -- 合同结束日期
    is_continuous       BOOLEAN         NOT NULL DEFAULT FALSE,       -- 是否连续中标
    continuous_count    INTEGER         DEFAULT 0,                    -- 连续中标次数
    source_url          VARCHAR(1000)   DEFAULT '',                   -- 中标公告原始链接
    created_at          TIMESTAMP       NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP       NOT NULL DEFAULT NOW(),

    -- 外键约束
    CONSTRAINT fk_historical_awards_purchaser
        FOREIGN KEY (purchaser_id) REFERENCES purchasers (id)
        ON DELETE RESTRICT ON UPDATE CASCADE
);

COMMENT ON TABLE  historical_awards                IS '历史中标记录表';
COMMENT ON COLUMN historical_awards.project_name   IS '中标项目名称';
COMMENT ON COLUMN historical_awards.purchaser_id   IS '采购方ID，关联 purchasers 表';
COMMENT ON COLUMN historical_awards.winner_name    IS '中标方公司名称';
COMMENT ON COLUMN historical_awards.winner_type    IS '中标方类型：头部常客 / 中小公司 / 新进入者';
COMMENT ON COLUMN historical_awards.bid_amount     IS '中标金额，单位：万元';
COMMENT ON COLUMN historical_awards.budget_amount  IS '招标预算金额，单位：万元';
COMMENT ON COLUMN historical_awards.discount_rate  IS '折扣率 = 中标金额 / 预算金额 × 100，单位%';
COMMENT ON COLUMN historical_awards.project_category IS '项目类别：品牌策略 / 创意设计 / 媒介投放 / 活动执行 / 内容制作 / 新媒体运营';
COMMENT ON COLUMN historical_awards.bid_open_date  IS '开标日期';
COMMENT ON COLUMN historical_awards.contract_start IS '合同生效日期';
COMMENT ON COLUMN historical_awards.contract_end   IS '合同到期日期';
COMMENT ON COLUMN historical_awards.is_continuous  IS '是否连续中标（同一采购方的连续项目）';
COMMENT ON COLUMN historical_awards.continuous_count IS '连续中标次数';

-- 按采购方 + 开标日期联合索引
CREATE INDEX idx_awards_purchaser_date
    ON historical_awards (purchaser_id, bid_open_date DESC);

-- 按中标方查询
CREATE INDEX idx_awards_winner
    ON historical_awards (winner_name);

-- 按中标方类型
CREATE INDEX idx_awards_winner_type
    ON historical_awards (winner_type);

-- 按项目类别
CREATE INDEX idx_awards_category
    ON historical_awards (project_category);

-- 按开标日期
CREATE INDEX idx_awards_date
    ON historical_awards (bid_open_date DESC);


-- ============================================================
-- 4. 客情记录表
-- ============================================================
CREATE TABLE client_relations (
    id                  SERIAL PRIMARY KEY,
    purchaser_id        INTEGER         NOT NULL,                     -- 采购方ID
    contact_name        VARCHAR(100)    NOT NULL,                     -- 联系人姓名
    title               VARCHAR(100),                                 -- 职位
    phone               VARCHAR(30),                                  -- 电话
    email               VARCHAR(200),                                 -- 邮箱
    last_contact_date   DATE            DEFAULT NULL,                 -- 最近接触时间
    contact_method      VARCHAR(20)     DEFAULT NULL,                 -- 接触方式
    contact_summary     TEXT,                                         -- 接触内容摘要
    rating              CHAR(1)         NOT NULL DEFAULT 'C',         -- 关系评级：S/A/B/C/D
    next_followup_date  DATE            DEFAULT NULL,                 -- 下次跟进提醒日期
    created_at          TIMESTAMP       NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP       NOT NULL DEFAULT NOW(),

    -- 外键约束
    CONSTRAINT fk_client_relations_purchaser
        FOREIGN KEY (purchaser_id) REFERENCES purchasers (id)
        ON DELETE RESTRICT ON UPDATE CASCADE,

    -- 评级约束
    CONSTRAINT chk_client_relations_rating
        CHECK (rating IN ('S', 'A', 'B', 'C', 'D'))
);

COMMENT ON TABLE  client_relations                    IS '客情关系记录表';
COMMENT ON COLUMN client_relations.purchaser_id       IS '采购方ID，关联 purchasers 表';
COMMENT ON COLUMN client_relations.contact_name       IS '采购方联系人姓名';
COMMENT ON COLUMN client_relations.title              IS '联系人职位/职称';
COMMENT ON COLUMN client_relations.phone              IS '联系电话';
COMMENT ON COLUMN client_relations.email              IS '电子邮箱';
COMMENT ON COLUMN client_relations.last_contact_date  IS '最近一次接触日期';
COMMENT ON COLUMN client_relations.contact_method     IS '接触方式：面谈 / 电话 / 微信 / 邮件 / 饭局';
COMMENT ON COLUMN client_relations.contact_summary    IS '接触内容摘要记录';
COMMENT ON COLUMN client_relations.rating             IS '关系评级：S（极好）/ A（好）/ B（较好）/ C（一般）/ D（差）';
COMMENT ON COLUMN client_relations.next_followup_date IS '下次跟进提醒日期，用于定时提醒';

-- 按采购方查询其所有联系人
CREATE INDEX idx_relations_purchaser
    ON client_relations (purchaser_id);

-- 按关系评级筛选
CREATE INDEX idx_relations_rating
    ON client_relations (rating);

-- 按下次跟进日期提醒
CREATE INDEX idx_relations_followup
    ON client_relations (next_followup_date);

-- 按最近接触时间排序
CREATE INDEX idx_relations_last_contact
    ON client_relations (last_contact_date DESC);


-- ============================================================
-- 5. 项目-客情关联提醒表
-- ============================================================
CREATE TABLE project_relation_alerts (
    id                SERIAL PRIMARY KEY,
    announcement_id   INTEGER       NOT NULL,                     -- 公告ID
    relation_id       INTEGER       NOT NULL,                     -- 客情记录ID
    alert_reason      TEXT          NOT NULL,                     -- 提醒原因
    is_read           BOOLEAN       NOT NULL DEFAULT FALSE,       -- 是否已读
    created_at        TIMESTAMP     NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMP     NOT NULL DEFAULT NOW(),

    -- 外键约束
    CONSTRAINT fk_alerts_announcement
        FOREIGN KEY (announcement_id) REFERENCES announcements (id)
        ON DELETE CASCADE ON UPDATE CASCADE,

    CONSTRAINT fk_alerts_relation
        FOREIGN KEY (relation_id) REFERENCES client_relations (id)
        ON DELETE CASCADE ON UPDATE CASCADE,

    -- 同一公告与同一客情关系只保留一条提醒
    CONSTRAINT uq_alerts_announcement_relation
        UNIQUE (announcement_id, relation_id)
);

COMMENT ON TABLE  project_relation_alerts                  IS '项目-客情关联提醒表';
COMMENT ON COLUMN project_relation_alerts.announcement_id  IS '关联的招标公告ID';
COMMENT ON COLUMN project_relation_alerts.relation_id      IS '关联的客情记录ID';
COMMENT ON COLUMN project_relation_alerts.alert_reason     IS '提醒原因，如："该采购方有对应客情关系，建议优先跟进"';
COMMENT ON COLUMN project_relation_alerts.is_read          IS '用户是否已读该提醒';

-- 按公告查询关联提醒
CREATE INDEX idx_alerts_announcement
    ON project_relation_alerts (announcement_id);

-- 按客情记录查询关联提醒
CREATE INDEX idx_alerts_relation
    ON project_relation_alerts (relation_id);

-- 按未读状态筛选
CREATE INDEX idx_alerts_unread
    ON project_relation_alerts (is_read, announcement_id)
    WHERE is_read = FALSE;


-- ============================================================
-- 触发器：自动更新 updated_at 字段
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 为所有表挂载自动更新触发器
CREATE TRIGGER trg_purchasers_updated_at
    BEFORE UPDATE ON purchasers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_announcements_updated_at
    BEFORE UPDATE ON announcements
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_historical_awards_updated_at
    BEFORE UPDATE ON historical_awards
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_client_relations_updated_at
    BEFORE UPDATE ON client_relations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_project_relation_alerts_updated_at
    BEFORE UPDATE ON project_relation_alerts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
