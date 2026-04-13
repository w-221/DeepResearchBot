# database.py - 数据库连接和操作模块
import os
import logging
from typing import Optional, List, Dict
import pymysql
from pymysql.cursors import DictCursor
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 日志配置
logger = logging.getLogger(__name__)

# 数据库连接配置
DB_HOST = os.getenv("MYSQL_HOST", "localhost")
DB_PORT = int(os.getenv("MYSQL_PORT", "3306"))
DB_USER = os.getenv("MYSQL_USER", "")
DB_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
DB_NAME = os.getenv("MYSQL_DATABASE", "")

# 连接池
connection_pool = None

def get_db_connection():
    """
    获取数据库连接

    Returns:
        pymysql.Connection: 数据库连接对象
    """
    try:
        connection = pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            charset='utf8mb4',
            cursorclass=DictCursor,
            autocommit=False
        )
        return connection
    except Exception as e:
        logger.error(f"数据库连接失败: {e}")
        raise


def execute_query(query: str, params: tuple = None, fetch: bool = False):
    """
    执行 SQL 查询

    Args:
        query: SQL 查询语句
        params: 查询参数
        fetch: 是否返回结果

    Returns:
        查询结果或影响行数
    """
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(query, params)

            if fetch:
                result = cursor.fetchall()
                connection.commit()
                return result
            else:
                connection.commit()
                return cursor.rowcount
    except Exception as e:
        logger.error(f"执行查询失败: {query}, 错误: {e}")
        if connection:
            connection.rollback()
        raise
    finally:
        if connection:
            connection.close()


def execute_batch_query(queries: List[str], params_list: List[tuple] = None):
    """
    批量执行 SQL 查询（事务）

    Args:
        queries: SQL 查询语句列表
        params_list: 查询参数列表

    Returns:
        成功执行的查询数量
    """
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            success_count = 0
            for i, query in enumerate(queries):
                params = params_list[i] if params_list else None
                cursor.execute(query, params)
                success_count += 1
            connection.commit()
            return success_count
    except Exception as e:
        logger.error(f"批量执行查询失败: {e}")
        if connection:
            connection.rollback()
        raise
    finally:
        if connection:
            connection.close()


def initialize_tables():
    """
    初始化数据库表结构
    """
    try:
        # 员工登录信息表
        create_employee_login_table()

        # 其他必要表的创建可以在这里添加
        logger.info("数据库表结构初始化成功")
        return True
    except Exception as e:
        logger.error(f"数据库表结构初始化失败: {e}")
        return False


def create_employee_login_table():
    """
    创建员工登录信息表
    """
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS `employee_login_info` (
        `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键ID',
        `email` VARCHAR(128) NOT NULL COMMENT '员工邮箱（登录用户名）',
        `password_hash` VARCHAR(255) NOT NULL COMMENT '密码哈希值（bcrypt）',
        `salt` VARCHAR(64) DEFAULT NULL COMMENT '密码盐值（预留）',
        `employee_id` VARCHAR(32) DEFAULT NULL COMMENT '员工工号（唯一标识）',
        `name` VARCHAR(64) DEFAULT NULL COMMENT '员工姓名',
        `department` VARCHAR(64) DEFAULT NULL COMMENT '所属部门',
        `phone` VARCHAR(20) DEFAULT NULL COMMENT '联系电话',
        `avatar` VARCHAR(255) DEFAULT NULL COMMENT '头像URL',
        `status` ENUM('active', 'locked', 'disabled', 'deleted') DEFAULT 'active' COMMENT '账户状态',
        `is_admin` TINYINT(1) DEFAULT 0 COMMENT '是否管理员',
        `failed_login_count` INT UNSIGNED DEFAULT 0 COMMENT '连续登录失败次数',
        `lock_until` DATETIME DEFAULT NULL COMMENT '账户锁定截止时间',
        `last_login_at` DATETIME DEFAULT NULL COMMENT '最后成功登录时间',
        `last_login_ip` VARCHAR(45) DEFAULT NULL COMMENT '最后登录IP地址',
        `verification_code` VARCHAR(10) DEFAULT NULL COMMENT '邮箱验证码',
        `verification_code_sent_at` DATETIME DEFAULT NULL COMMENT '验证码发送时间',
        `email_verified_at` DATETIME DEFAULT NULL COMMENT '邮箱验证时间',
        `verification_code_failed_count` INT UNSIGNED DEFAULT 0 COMMENT '验证码错误次数',
        `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
        `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
        PRIMARY KEY (`id`),
        UNIQUE KEY `uk_email` (`email`),
        KEY `idx_status` (`status`),
        KEY `idx_employee_id` (`employee_id`),
        KEY `idx_created_at` (`created_at`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='员工登录信息表';
    """

    execute_query(create_table_sql)

    # 创建索引（如果需要额外索引）- 先检查是否已存在
    try:
        # 检查索引是否已存在
        result = execute_query(
            "SHOW INDEX FROM employee_login_info WHERE Key_name = 'idx_lock_until'",
            fetch=True
        )
        if not result:
            # 索引不存在，创建它
            execute_query("CREATE INDEX idx_lock_until ON employee_login_info(lock_until)")
    except Exception:
        pass  # 忽略任何错误


def test_connection():
    """
    测试数据库连接

    Returns:
        bool: 连接是否成功
    """
    try:
        connection = get_db_connection()
        if connection:
            connection.close()
            logger.info("数据库连接测试成功")
            return True
        return False
    except Exception as e:
        logger.error(f"数据库连接测试失败: {e}")
        return False


if __name__ == "__main__":
    # 测试数据库连接
    print("测试数据库连接...")
    if test_connection():
        print("数据库连接成功!")

        # 初始化表结构
        print("初始化表结构...")
        if initialize_tables():
            print("表结构初始化成功!")
        else:
            print("表结构初始化失败!")
    else:
        print("数据库连接失败!")