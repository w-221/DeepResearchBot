# email_service.py - 邮件发送服务
import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from typing import Optional

from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 日志
logger = logging.getLogger(__name__)

# SMTP 配置
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.163.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "noreply@company.com")
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
EMAIL_SUBJECT_PREFIX = os.getenv("EMAIL_SUBJECT_PREFIX", "[沃华医药]")


class EmailService:
    """邮件服务类"""

    def __init__(self):
        self.smtp_server = SMTP_SERVER
        self.smtp_port = SMTP_PORT
        self.smtp_user = SMTP_USER
        self.smtp_password = SMTP_PASSWORD
        self.smtp_from = SMTP_FROM
        self.use_tls = SMTP_USE_TLS

    def _create_connection(self):
        """
        创建 SMTP 连接

        Returns:
            smtplib.SMTP: SMTP 连接对象
        """
        try:
            if self.smtp_port == 465:
                # SSL 连接
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
            else:
                # TLS 或普通连接
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)

            if self.use_tls:
                server.starttls()

            if self.smtp_user and self.smtp_password:
                server.login(self.smtp_user, self.smtp_password)

            return server
        except Exception as e:
            logger.error(f"SMTP 连接失败: {e}")
            raise Exception(f"邮件服务器连接失败: {str(e)}")

    def _send_email(self, to_email: str, subject: str, body: str, html_body: Optional[str] = None) -> bool:
        """
        发送邮件

        Args:
            to_email: 收件人邮箱
            subject: 邮件主题
            body: 纯文本内容
            html_body: HTML 内容（可选）

        Returns:
            bool: 是否发送成功
        """
        server = None
        try:
            server = self._create_connection()

            # 创建邮件
            msg = MIMEMultipart('alternative')
            msg['From'] = formataddr(('沃华医药', self.smtp_from))
            msg['To'] = to_email
            msg['Subject'] = f"{EMAIL_SUBJECT_PREFIX} {subject}"

            # 添加纯文本部分
            text_part = MIMEText(body, 'plain', 'utf-8')
            msg.attach(text_part)

            # 如果有 HTML 内容，添加 HTML 部分
            if html_body:
                html_part = MIMEText(html_body, 'html', 'utf-8')
                msg.attach(html_part)

            # 发送邮件
            server.send_message(msg)

            logger.info(f"邮件发送成功: to={to_email}, subject={subject}")
            return True

        except Exception as e:
            logger.error(f"邮件发送失败: {e}")
            return False
        finally:
            if server:
                try:
                    server.quit()
                except:
                    pass

    async def send_verification_email(self, email: str, code: str) -> bool:
        """
        发送验证码邮件

        Args:
            email: 收件人邮箱
            code: 6位数字验证码

        Returns:
            bool: 是否发送成功
        """
        subject = "邮箱验证码"
        expiry_minutes = 5  # 验证码5分钟有效

        # 纯文本内容
        text_body = f"""尊敬的用户，您好！

您的邮箱验证码是：{code}

验证码有效期为：{expiry_minutes}分钟。

如果这不是您本人操作，请忽略此邮件。

此邮件由系统自动发送，请勿回复。
沃华医药
"""

        # HTML 内容
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .container {{
            background: #f5f5f5;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
        }}
        .logo {{
            font-size: 24px;
            color: #4a90e2;
            font-weight: bold;
        }}
        .code-box {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            text-align: center;
            border-radius: 8px;
            margin: 30px 0;
        }}
        .code {{
            font-size: 36px;
            font-weight: bold;
            letter-spacing: 8px;
        }}
        .info {{
            text-align: center;
            color: #666;
            margin-top: 20px;
        }}
        .footer {{
            text-align: center;
            margin-top: 30px;
            color: #999;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">沃华医药</div>
            <p>邮箱验证码</p>
        </div>
        <div class="code-box">
            <div class="code">{code}</div>
        </div>
        <div class="info">
            验证码有效期为 {expiry_minutes} 分钟
        </div>
        <div class="footer">
            <p>如果这不是您本人操作，请忽略此邮件</p>
            <p>此邮件由系统自动发送，请勿回复</p>
            <p>© 2024 沃华医药</p>
        </div>
    </div>
</body>
</html>
"""

        return self._send_email(email, subject, text_body, html_body)

    async def send_welcome_email(self, email: str, name: str) -> bool:
        """
        发送欢迎邮件

        Args:
            email: 收件人邮箱
            name: 用户姓名

        Returns:
            bool: 是否发送成功
        """
        subject = "注册成功，欢迎加入沃华医药"

        text_body = f"""尊敬的{name}，您好！

恭喜您成功注册成为沃华医药的用户！

您的登录邮箱：{email}

如有任何问题，请联系客服。

此邮件由系统自动发送，请勿回复。
沃华医药
"""

        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .container {{
            background: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
        }}
        .logo {{
            font-size: 32px;
            color: #4a90e2;
            font-weight: bold;
            margin-bottom: 10px;
        }}
        .welcome {{
            font-size: 24px;
            color: #667eea;
        }}
        .info {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 4px;
            margin: 20px 0;
        }}
        .info-item {{
            margin: 10px 0;
        }}
        .info-label {{
            font-weight: bold;
            color: #666;
        }}
        .info-value {{
            color: #333;
        }}
        .footer {{
            text-align: center;
            margin-top: 40px;
            color: #999;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">沃华医药</div>
            <div class="welcome">欢迎加入！</div>
        </div>
        <div class="info">
            <div class="info-item">
                <span class="info-label">用户姓名：</span>
                <span class="info-value">{name}</span>
            </div>
            <div class="info-item">
                <span class="info-label">登录邮箱：</span>
                <span class="info-value">{email}</span>
            </div>
        </div>
        <div class="footer">
            <p>如有任何问题，请联系客服</p>
            <p>此邮件由系统自动发送，请勿回复</p>
            <p>© 2024 沃华医药</p>
        </div>
    </div>
</body>
</html>
"""

        return self._send_email(email, subject, text_body, html_body)


# 全局邮件服务实例
email_service = EmailService()


async def send_verification_email(email: str, code: str) -> bool:
    """
    发送验证码邮件（全局函数）

    Args:
        email: 收件人邮箱
        code: 验证码

    Returns:
        bool: 是否发送成功
    """
    return await email_service.send_verification_email(email, code)


def send_welcome_email(email: str, name: str) -> bool:
    """
    发送欢迎邮件（同步函数）

    Args:
        email: 收件人邮箱
        name: 用户姓名

    Returns:
        bool: 是否发送成功
    """
    import asyncio
    return asyncio.run(email_service.send_welcome_email(email, name))


# 测试邮件发送
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        test_email = sys.argv[1]
        print(f"发送测试邮件到: {test_email}")

        async def test():
            result = await send_verification_email(test_email, "123456")
            print(f"发送结果: {'成功' if result else '失败'}")

        import asyncio
        asyncio.run(test())
    else:
        print("使用方法: python api/email_service.py <test_email>")