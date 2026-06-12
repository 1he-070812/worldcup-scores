#!/usr/bin/env python3
"""
2026 世界杯每日比分推送脚本
适用平台：GitHub Actions / 任何 Linux/Mac/Windows 定时任务
依赖：pip install requests beautifulsoup4
"""

import os
import re
import smtplib
import sys
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.header import Header

import requests
from bs4 import BeautifulSoup

# ── 配置项（通过环境变量传入，不要写在代码里）──
SMTP_USER = os.environ.get("QQ_SMTP_USER", "")       # QQ邮箱完整地址
SMTP_PASS = os.environ.get("QQ_SMTP_PASS", "")        # SMTP授权码（不是登录密码）
MAIL_TO   = os.environ.get("MAIL_TO", SMTP_USER)      # 收件地址，默认发给自己


# ── 抓取来源 ──
SOURCES = [
    "https://worldcuplocaltime.com/fifa-world-cup-2026-results/",
    "https://worldcupranking.com/world-cup-2026/results/",
]

def fetch_results() -> str:
    """从多个来源抓取比赛结果，返回纯文本报告"""
    for url in SOURCES:
        try:
            resp = requests.get(url, timeout=15, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            resp.encoding = "utf-8"
            soup = BeautifulSoup(resp.text, "html.parser")
            text = soup.get_text(separator="\n", strip=True)
            # 如果包含比分模式如 "2-0" 并且包含常见队伍关键字，说明有数据
            if re.search(r"\d+[-–]\d+", text) and ("Mexico" in text or "Korea" in text or "Brazil" in text):
                return _parse_scores(text)
        except Exception as e:
            continue
    return "⚠️ 暂时无法获取最新比分数据，请稍后再试。"

def _parse_scores(raw: str) -> str:
    """将原始文本解析为格式化报告"""
    lines = raw.split("\n")
    report_parts = []
    current_date = ""

    # 简单匹配："Mexico 2-0 South Africa" 这类格式
    score_pattern = re.compile(r"([A-Za-z\s]+?)\s+(\d+)[\s]*[-–][\s]*(\d+)\s+([A-Za-z\s]+)")

    for line in lines:
        line = line.strip()
        # 尝试匹配日期行
        if re.match(r"^(June|July)\s+\d+", line, re.IGNORECASE):
            current_date = line
            report_parts.append(f"\n📅 {current_date}")
            report_parts.append("─" * 40)
        # 尝试匹配比分
        m = score_pattern.search(line)
        if m:
            team1, score1, score2, team2 = m.groups()
            emoji1 = _flag_emoji(team1.strip())
            emoji2 = _flag_emoji(team2.strip())
            report_parts.append(f"  {emoji1} {team1.strip()} {score1}-{score2} {team2.strip()} {emoji2}")

    if not report_parts:
        return raw  # fallback

    return "\n".join(report_parts)

def _flag_emoji(country: str) -> str:
    """简易队伍→国旗映射"""
    mapping = {
        "Mexico": "🇲🇽", "South Africa": "🇿🇦",
        "Korea": "🇰🇷", "South Korea": "🇰🇷", "Czech": "🇨🇿", "Czech Republic": "🇨🇿",
        "Canada": "🇨🇦", "Bosnia": "🇧🇦",
        "USA": "🇺🇸", "United States": "🇺🇸", "Paraguay": "🇵🇾",
        "Brazil": "🇧🇷", "Morocco": "🇲🇦",
        "England": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "Argentina": "🇦🇷",
        "France": "🇫🇷", "Germany": "🇩🇪", "Spain": "🇪🇸",
        "Portugal": "🇵🇹", "Netherlands": "🇳🇱", "Belgium": "🇧🇪",
        "Japan": "🇯🇵", "Australia": "🇦🇺",
        "Saudi Arabia": "🇸🇦", "Iran": "🇮🇷",
    }
    for kw, emoji in mapping.items():
        if kw.lower() in country.lower():
            return emoji
    return "🏳️"

def send_mail(subject: str, body: str):
    """通过 QQ 邮箱 SMTP 发送邮件"""
    if not SMTP_USER or not SMTP_PASS:
        print("❌ 未配置 QQ_SMTP_USER 或 QQ_SMTP_PASS，跳过发送")
        print("=== 邮件内容预览 ===")
        print(body)
        return

    msg = MIMEText(body, "plain", "utf-8")
    msg["From"] = SMTP_USER
    msg["To"] = MAIL_TO
    msg["Subject"] = Header(subject, "utf-8")

    try:
        server = smtplib.SMTP_SSL("smtp.qq.com", 465, timeout=30)
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, [MAIL_TO], msg.as_string())
        server.quit()
        print(f"✅ 邮件已发送至 {MAIL_TO}")
    except Exception as e:
        print(f"❌ 发送失败: {e}")
        sys.exit(1)


def main():
    today = datetime.now(timezone.utc).strftime("%m月%d日")
    print(f"📡 正在获取 2026 世界杯比分… ({today})")

    report = fetch_results()

    subject = f"⚽ 2026世界杯比分日报 - {today}"
    full_body = (
        f"━━━━━━━━━━━━━━━\n"
        f"  ⚽ 2026 FIFA 世界杯 比分日报\n"
        f"  📆 {today}\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"{report}\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"⚡ 自动推送 · 每日更新\n"
    )

    print(full_body)
    send_mail(subject, full_body)


if __name__ == "__main__":
    main()
