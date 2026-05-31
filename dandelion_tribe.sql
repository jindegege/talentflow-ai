-- 1. 创建数据库
CREATE DATABASE IF NOT EXISTS dandelion_tribe 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

USE dandelion_tribe;

-- ==========================================
-- 2. 基础数据表：技能字典
-- 描述：存储标准化的技能标签，是匹配算法的基石
-- ==========================================
CREATE TABLE `skills` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT '技能ID',
    `name` VARCHAR(50) NOT NULL COMMENT '技能名称 (如: Python, Vue3)',
    `category` VARCHAR(30) NOT NULL COMMENT '分类 (如: Language, Framework)',
    `parent_id` INT DEFAULT NULL COMMENT '父技能ID (用于构建层级关系)',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_name` (`name`),
    KEY `idx_category` (`category`),
    KEY `idx_parent_id` (`parent_id`),
    CONSTRAINT `fk_skill_parent` FOREIGN KEY (`parent_id`) REFERENCES `skills` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='技能字典表';

-- ==========================================
-- 3. 用户中心表
-- ==========================================
CREATE TABLE `users` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT '用户ID',
    `username` VARCHAR(50) NOT NULL COMMENT '用户名',
    `email` VARCHAR(100) NOT NULL COMMENT '邮箱 (登录账号)',
    `password_hash` VARCHAR(255) NOT NULL COMMENT '密码哈希值',
    `role` VARCHAR(20) DEFAULT 'candidate' COMMENT '角色: candidate, mentor, admin',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '注册时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_username` (`username`),
    UNIQUE KEY `uk_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户基础信息表';

-- ==========================================
-- 4. 简历表 (核心资产)
-- 描述：存储简历详细内容，支持一人多简历，是AI分析的主要对象
-- ==========================================
CREATE TABLE `resumes` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT '简历ID',
    `user_id` INT NOT NULL COMMENT '所属用户ID',
    `title` VARCHAR(100) NOT NULL COMMENT '简历标题 (如: Java后端简历)',
    `summary` TEXT COMMENT '个人总结 (用于向量检索)',
    `project_experience` TEXT COMMENT '项目经历 (用于AI生成求职信)',
    `education` TEXT COMMENT '教育背景',
    `is_default` TINYINT(1) DEFAULT 0 COMMENT '是否为默认简历 (0:否, 1:是)',
    `vector_id` VARCHAR(64) DEFAULT NULL COMMENT '关联向量数据库的ID (用于RAG)',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_user_id` (`user_id`),
    CONSTRAINT `fk_resume_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='简历详情表';

-- ==========================================
-- 5. 用户技能关联表
-- 描述：记录用户（或特定简历）掌握的技能及熟练度
-- ==========================================
CREATE TABLE `user_skills` (
    `user_id` INT NOT NULL COMMENT '用户ID',
    `resume_id` INT DEFAULT NULL COMMENT '所属简历ID (若为空则代表全局技能)',
    `skill_id` INT NOT NULL COMMENT '技能ID',
    `proficiency` INT DEFAULT 1 COMMENT '熟练度 (1-5)',
    `source` VARCHAR(20) DEFAULT 'manual' COMMENT '来源: resume(解析), task(实战), manual(手动)',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`user_id`, `skill_id`),
    KEY `idx_skill_id` (`skill_id`),
    KEY `idx_resume_id` (`resume_id`),
    CONSTRAINT `fk_us_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_us_skill` FOREIGN KEY (`skill_id`) REFERENCES `skills` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_us_resume` FOREIGN KEY (`resume_id`) REFERENCES `resumes` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户技能关联表';

-- ==========================================
-- 6. 职位表
-- 描述：存储爬取及清洗后的职位信息
-- ==========================================
CREATE TABLE `jobs` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT '职位ID',
    `title` VARCHAR(100) NOT NULL COMMENT '职位名称',
    `company` VARCHAR(100) NOT NULL COMMENT '公司名称',
    `description` TEXT COMMENT '职位描述 (用于向量化)',
    `location` VARCHAR(50) DEFAULT NULL COMMENT '工作地点',
    `salary_range` VARCHAR(50) DEFAULT NULL COMMENT '薪资范围',
    `source_url` VARCHAR(255) DEFAULT NULL COMMENT '原始链接',
    `vector_id` VARCHAR(64) DEFAULT NULL COMMENT '关联向量数据库的ID',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    FULLTEXT KEY `ft_description` (`description`) -- MySQL 全文索引备用
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='职位信息表';

-- ==========================================
-- 7. 投递记录表
-- 描述：记录AI或用户的投递行为
-- ==========================================
CREATE TABLE `applications` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT '投递ID',
    `user_id` INT NOT NULL COMMENT '用户ID',
    `job_id` INT NOT NULL COMMENT '职位ID',
    `resume_id` INT NOT NULL COMMENT '使用的简历ID',
    `status` VARCHAR(20) DEFAULT 'applied' COMMENT '状态: applied, interview, rejected',
    `cover_letter` TEXT COMMENT 'AI生成的求职信',
    `applied_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '投递时间',
    PRIMARY KEY (`id`),
    KEY `idx_user_id` (`user_id`),
    KEY `idx_job_id` (`job_id`),
    KEY `idx_resume_id` (`resume_id`),
    CONSTRAINT `fk_app_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`),
    CONSTRAINT `fk_app_job` FOREIGN KEY (`job_id`) REFERENCES `jobs` (`id`),
    CONSTRAINT `fk_app_resume` FOREIGN KEY (`resume_id`) REFERENCES `resumes` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='投递记录表';

-- ==========================================
-- 8. 实战任务表
-- 描述：企业发布的实战项目
-- ==========================================
CREATE TABLE `tasks` (
    `id` INT NOT NULL AUTO_INCREMENT COMMENT '任务ID',
    `title` VARCHAR(150) NOT NULL COMMENT '任务标题',
    `description` TEXT COMMENT '任务描述',
    `required_skills` VARCHAR(255) DEFAULT NULL COMMENT '所需技能 (逗号分隔或JSON)',
    `status` VARCHAR(20) DEFAULT 'active' COMMENT '状态: active, completed, archived',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='实战任务表';

-- ==========================================
-- 9. 任务交付表
-- 描述：用户提交的任务成果
-- ==========================================
CREATE TABLE `task_deliveries` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `task_id` INT NOT NULL,
    `user_id` INT NOT NULL,
    `delivery_url` VARCHAR(255) COMMENT '交付物链接 (GitHub等)',
    `comment` TEXT COMMENT '用户备注',
    `status` VARCHAR(20) DEFAULT 'submitted' COMMENT '状态: submitted, reviewed',
    `submitted_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_task_id` (`task_id`),
    KEY `idx_user_id` (`user_id`),
    CONSTRAINT `fk_td_task` FOREIGN KEY (`task_id`) REFERENCES `tasks` (`id`),
    CONSTRAINT `fk_td_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='任务交付表';