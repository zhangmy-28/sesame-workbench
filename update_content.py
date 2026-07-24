#!/usr/bin/env python3
"""
芝麻油工作台 - 每日内容自动抓取脚本
通过 GitHub Actions 每天定时运行，从公开 RSS/API 获取最新资讯
"""

import json
import os
import sys
import hashlib
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
import xml.etree.ElementTree as ET
import re
import time
import random

# ===== 配置 =====
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), 'data.json')
USER_AGENT = 'Mozilla/5.0 (compatible; SesameWorkbench/1.0; +https://github.com/zhangmy-28/sesame-workbench)'

# ===== 工具函数 =====
def fetch_url(url, timeout=15, retries=2):
    """带重试的 URL 抓取"""
    for attempt in range(retries + 1):
        try:
            req = Request(url, headers={'User-Agent': USER_AGENT})
            with urlopen(req, timeout=timeout) as resp:
                return resp.read().decode('utf-8', errors='ignore')
        except Exception as e:
            if attempt == retries:
                print(f"  ⚠ 获取失败 {url}: {e}")
                return None
            time.sleep(2)

def parse_rss(xml_text):
    """解析 RSS/Atom XML"""
    if not xml_text:
        return []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []
    
    items = []
    # RSS 2.0
    for item in root.iter('item'):
        title = item.findtext('title', '')
        link = item.findtext('link', '')
        desc = item.findtext('description', '')
        pubdate = item.findtext('pubDate', '')
        # 清理 HTML 标签
        desc = re.sub(r'<[^>]+>', '', desc)
        desc = re.sub(r'\s+', ' ', desc).strip()
        if title and link:
            items.append({
                'title': title.strip(),
                'link': link.strip(),
                'description': desc[:300],
                'pubDate': pubdate
            })
    
    # Atom
    ns = {'atom': 'http://www.w3.org/2005/Atom'}
    for entry in root.findall('atom:entry', ns) or root.findall('{http://www.w3.org/2005/Atom}entry'):
        title = entry.findtext('{http://www.w3.org/2005/Atom}title', '') or entry.findtext('atom:title', '')
        link_el = entry.find('{http://www.w3.org/2005/Atom}link') or entry.find('atom:link')
        link = link_el.get('href', '') if link_el is not None else ''
        desc = entry.findtext('{http://www.w3.org/2005/Atom}summary', '') or entry.findtext('atom:summary', '')
        desc = re.sub(r'<[^>]+>', '', desc)
        desc = re.sub(r'\s+', ' ', desc).strip()
        if title and link:
            items.append({
                'title': title.strip(),
                'link': link.strip(),
                'description': desc[:300],
                'pubDate': ''
            })
    
    return items

# ===== 各分类抓取函数 =====

def fetch_tech_finance():
    """抓取科技股/基金资讯 - 使用多个可靠RSS源"""
    print("[科技基金] 抓取中...")
    items = []
    
    # 华尔街见闻 - 最新资讯
    rss_urls = [
        'https://rsshub.rssforever.com/wallstreetcn/global/1',
        'https://feedx.net/rss/36kr.xml',
    ]
    
    for url in rss_urls:
        xml_text = fetch_url(url)
        if xml_text:
            items.extend(parse_rss(xml_text))
    
    # 如果没有 RSS 数据，使用预置的模板
    if not items:
        items = get_fallback_tech()
    else:
        # 过滤出科技/财经相关
        items = [i for i in items if any(kw in i.get('title','')+i.get('description','') for kw in ['科技','AI','芯片','美股','基金','纳指','英伟达','苹果','谷歌','微软','特斯拉','半导体','算力','港股','A股','投资'])]
        if not items:
            items = get_fallback_tech()
        else:
            items = items[:4]
    
    print(f"  ✓ 获取 {len(items)} 条")
    return items

def fetch_trade_news():
    """抓取外贸/国际资讯 - 使用多个可靠RSS源"""
    print("[外贸资讯] 抓取中...")
    items = []
    
    rss_urls = [
        'https://feedx.net/rss/cls.xml',
        'https://rsshub.rssforever.com/wallstreetcn/global/1',
    ]
    
    for url in rss_urls:
        xml_text = fetch_url(url)
        if xml_text:
            items.extend(parse_rss(xml_text))
    
    if not items:
        items = get_fallback_trade()
    else:
        items = items[:5]
    
    print(f"  ✓ 获取 {len(items)} 条")
    return items

def fetch_speaking():
    """每日口语（轮换场景）"""
    print("[口语练习] 生成中...")
    # 口语内容从预设场景库轮换
    return get_daily_speaking()

def fetch_listening():
    """每日听力（轮换场景）"""
    print("[听力练习] 生成中...")
    return get_daily_listening()

def fetch_fashion():
    """穿搭灵感（轮换）"""
    print("[穿搭灵感] 生成中...")
    return get_daily_fashion()

def fetch_blog():
    """博客推荐"""
    print("[博客推荐] 抓取中...")
    items = []
    
    rss_urls = [
        'https://feedx.net/rss/sspai.xml',
        'https://feedx.net/rss/36kr.xml',
    ]
    
    for url in rss_urls:
        xml_text = fetch_url(url)
        if xml_text:
            items.extend(parse_rss(xml_text))
    
    if not items:
        items = get_fallback_blog()
    else:
        items = items[:5]
    
    print(f"  ✓ 获取 {len(items)} 条")
    return items

# ===== 兜底内容（当RSS抓取失败时使用）=====

def get_fallback_tech():
    return [
        {
            'title': '美股三大指数最新行情（模板）',
            'link': 'https://wap.eastmoney.com/quote/stock/100.NDX.html',
            'description': '请等待GitHub Actions首次运行后自动抓取最新数据。每日北京时间8:00自动更新。',
            'source': '东方财富'
        }
    ]

def get_fallback_trade():
    return [
        {
            'title': '外贸资讯（模板）',
            'link': 'https://finance.sina.com.cn/',
            'description': '请等待GitHub Actions首次运行后自动抓取最新数据。每日北京时间8:00自动更新。',
            'source': '新浪财经'
        }
    ]

def get_fallback_blog():
    return [
        {
            'title': '博客推荐（模板）',
            'link': 'https://zhuanlan.zhihu.com',
            'description': '请等待GitHub Actions首次运行后自动抓取最新数据。每日北京时间8:00自动更新。',
            'source': '知乎'
        }
    ]

# ===== 预设内容库 =====

def get_daily_speaking():
    """每日口语 - 根据日期轮换"""
    today = datetime.now()
    idx = today.timetuple().tm_yday % len(SPEAKING_SCENES)
    return SPEAKING_SCENES[idx]

SPEAKING_SCENES = [
    {
        'scenes': [
            {
                'title': '🏨 帮客户订酒店',
                'dialogue': [
                    {'speaker': 'You', 'text': "Good morning, Mr. Smith! Have you settled in well? How's the hotel?"},
                    {'speaker': 'Client', 'text': 'Good morning! Yes, the room is lovely. Thank you for arranging it.'},
                    {'speaker': 'You', 'text': "I'm glad you like it. I chose a room with a city view — the night scenery here is quite beautiful."},
                    {'speaker': 'Client', 'text': 'Oh, I noticed! The skyline at night is stunning. Great choice!'},
                    {'speaker': 'You', 'text': "If you need anything — laundry, gym access, or restaurant recommendations — just let me know."}
                ],
                'tips': '💡 关键短语：settle in（安顿下来）、city view（城市景观）、I\'m happy to help（我很乐意帮忙）'
            }
        ],
        'culture_tip': {
            'title': '跨文化小贴士：中东客户篇',
            'points': [
                '🕌 尊重宗教习惯：注意祈祷时间，不要在此时段安排会议',
                '🤝 握手礼仪：中东男性通常不和女性握手，可用点头微笑代替',
                '🎁 送礼注意：避免酒类、猪肉制品，茶叶和高品质文具是不错的选择',
                '⏰ 时间观念：部分中东国家时间观念较灵活，会议可能延迟，保持耐心',
                '💬 寒暄很重要：先问候家人、聊聊旅行，建立关系后再谈正事'
            ]
        }
    },
    {
        'scenes': [
            {
                'title': '🍽️ 商务午餐闲聊',
                'dialogue': [
                    {'speaker': 'You', 'text': "Have you tried any local dishes since you arrived?"},
                    {'speaker': 'Client', 'text': "Not yet! I've been looking forward to it. Any recommendations?"},
                    {'speaker': 'You', 'text': "Absolutely. I'd recommend the steamed fish — it's a local specialty, very light and fresh."},
                    {'speaker': 'Client', 'text': 'Sounds perfect. I prefer lighter food, especially in this summer heat.'},
                    {'speaker': 'You', 'text': "Great! And don't worry about spice levels — I'll ask them to keep it mild for you."}
                ],
                'tips': '💡 关键短语：local specialty（当地特色）、light and fresh（清淡新鲜）、keep it mild（口味清淡些）'
            }
        ],
        'culture_tip': {
            'title': '跨文化小贴士：日本客户篇',
            'points': [
                '🎌 交换名片：双手递上，名片正面朝向对方，收到后仔细看几秒再收好',
                '🙇 鞠躬礼仪：微微鞠躬表示尊重，不需要太深',
                '🍵 宴请礼仪：等长辈/上级先动筷，不要把筷子插在饭里',
                '⏰ 守时：日本人非常重视准时，提前5分钟到达最佳',
                '💼 决策流程：日本公司决策链较长，耐心等待，不要催促'
            ]
        }
    },
    {
        'scenes': [
            {
                'title': '✈️ 机场接机寒暄',
                'dialogue': [
                    {'speaker': 'You', 'text': 'Welcome to Shanghai! Did you have a smooth flight?'},
                    {'speaker': 'Client', 'text': 'Yes, thank you. It was about 14 hours, but I managed to get some sleep.'},
                    {'speaker': 'You', 'text': "That's good to hear. The car is waiting outside. Shall we head to the hotel first?"},
                    {'speaker': 'Client', 'text': 'That would be great. I could use a shower and a change of clothes.'},
                    {'speaker': 'You', 'text': 'Of course. The hotel is about 30 minutes from here. We can discuss the schedule on the way.'}
                ],
                'tips': '💡 关键短语：smooth flight（顺利的飞行）、head to（前往）、could use（想要/需要）'
            }
        ],
        'culture_tip': {
            'title': '跨文化小贴士：欧美客户篇',
            'points': [
                '👋 见面礼仪：握手要有力、眼神交流、面带微笑',
                '📧 沟通习惯：欧美客户倾向直接坦诚的沟通方式，不喜欢拐弯抹角',
                '🕐 时间管理：准时非常重要，迟到会被视为不专业',
                '📊 谈判风格：注重数据和事实支撑，不喜欢空泛的承诺',
                '🏠 私人空间：保持适当身体距离（约一臂），不要过于亲密'
            ]
        }
    },
    {
        'scenes': [
            {
                'title': '📞 电话跟进订单进度',
                'dialogue': [
                    {'speaker': 'You', 'text': "Hi David, just calling to update you on your order. Production is right on schedule."},
                    {'speaker': 'Client', 'text': "That's great to hear. Any chance we could get a partial shipment earlier?"},
                    {'speaker': 'You', 'text': "Let me check... Yes, we can ship 60% by next Friday, and the rest the following week."},
                    {'speaker': 'Client', 'text': 'Perfect. And the quality inspection — is that all done?'},
                    {'speaker': 'You', 'text': 'Absolutely. All items passed QC yesterday. I can send you the report right now.'}
                ],
                'tips': '💡 关键短语：on schedule（按计划）、partial shipment（分批装运）、QC report（质检报告）'
            }
        ],
        'culture_tip': {
            'title': '跨文化小贴士：拉美客户篇',
            'points': [
                '🤗 热情问候：拉美客户通常很热情，拥抱贴面礼很常见',
                '☕ 闲聊文化：不要一上来就谈业务，先喝杯咖啡聊聊生活和足球',
                '⏰ 弹性时间：会议可能延迟15-30分钟，这是文化习惯，不要表现出不耐烦',
                '👨‍👩‍👧 家庭观念：问候对方家人是拉近关系的好方式',
                '🤝 关系优先：拉美客户更看重个人关系而非合同条款'
            ]
        }
    },
    {
        'scenes': [
            {
                'title': '🏭 工厂参观接待',
                'dialogue': [
                    {'speaker': 'You', 'text': "Welcome to our factory! Let me give you a quick safety briefing first. Please put on this helmet and vest."},
                    {'speaker': 'Client', 'text': 'Sure. I have to say, the facility looks very impressive from the outside.'},
                    {'speaker': 'You', 'text': "Thank you! We've recently upgraded our production line. Let me walk you through the process — from raw material to finished product."},
                    {'speaker': 'Client', 'text': 'How many units can you produce per day at full capacity?'},
                    {'speaker': 'You', 'text': "Currently about 5,000 units per day. With the new equipment coming next month, we'll reach 8,000."}
                ],
                'tips': '💡 关键短语：safety briefing（安全须知）、walk through（走一遍/参观）、full capacity（满产）'
            }
        ],
        'culture_tip': {
            'title': '跨文化小贴士：东南亚客户篇',
            'points': [
                '🙏 合十礼：泰国等国家用合十礼代替握手，双手合十于胸前',
                '👣 脚部禁忌：不要把脚底朝向他人，也不要用脚指东西',
                '🗣️ 保全面子：避免公开批评或让人难堪，用委婉方式提建议',
                '🎁 小礼物：拜访时带点家乡特产或公司小礼品，很受欢迎',
                '📱 社交沟通：WhatsApp/Line 比邮件更常用，回复速度也更快'
            ]
        }
    }
]

def get_daily_listening():
    """每日听力 - 根据日期轮换"""
    today = datetime.now()
    idx = today.timetuple().tm_yday % len(LISTENING_SCENES)
    return LISTENING_SCENES[idx]

LISTENING_SCENES = [
    {
        'level': 1,
        'level_text': 'Level 1 · 基础',
        'difficulty': '★☆☆☆☆',
        'title': 'Greeting a Visitor at the Airport',
        'speed': '慢',
        'duration': '约45秒',
        'text': "A: Welcome to Shanghai! Did you have a smooth flight?\nB: Yes, thank you. It was about 14 hours, but I managed to get some sleep.\nA: That's good to hear. The car is waiting outside. Shall we head to the hotel first?\nB: That would be great. I could use a shower and a change of clothes.\nA: Of course. The hotel is about 30 minutes from here. We can discuss the schedule on the way.",
        'vocab': ['smooth flight（顺利的飞行）', 'head to（前往）', 'could use（想要/需要）'],
        'tags': ['接机', '初级']
    },
    {
        'level': 2,
        'level_text': 'Level 2 · 进阶',
        'difficulty': '★★☆☆☆',
        'title': 'Discussing Product Samples',
        'speed': '中等',
        'duration': '约1分钟',
        'text': "A: I've brought the latest samples for you to review. The fabric quality has been upgraded.\nB: Oh, this feels much softer than the last batch. What's the composition?\nA: It's 95% organic cotton with 5% elastane for stretch. The minimum order quantity is 500 pieces per design.\nB: That's reasonable. And what about the lead time?\nA: Typically 25-30 days after order confirmation. We can expedite to 20 days for an additional 10%.",
        'vocab': ['upgrade（升级）', 'composition（成分）', 'lead time（交货期）', 'expedite（加快）'],
        'tags': ['产品样品', '中级']
    },
    {
        'level': 3,
        'level_text': 'Level 3 · 进阶',
        'difficulty': '★★★☆☆',
        'title': 'Negotiating Price Terms',
        'speed': '中等偏快',
        'duration': '约1分15秒',
        'text': "A: We've reviewed your quotation and it's a bit above our budget. Is there room for negotiation?\nB: I understand. May I ask what target price you have in mind?\nA: We're looking at around $12.50 per unit for an order of 5,000 pieces.\nB: That's quite a stretch. At that volume, the best I can offer is $13.20, and that includes free shipping.\nA: If we increase the order to 8,000, can you meet us at $12.80?\nB: Let me check with our production team and get back to you by tomorrow. But I think we can work something out.",
        'vocab': ['quotation（报价）', 'room for negotiation（议价空间）', 'target price（目标价）', 'work something out（找到解决方案）'],
        'tags': ['价格谈判', '中级+']
    },
    {
        'level': 1,
        'level_text': 'Level 1 · 基础',
        'difficulty': '★☆☆☆☆',
        'title': 'Ordering Coffee at a Café',
        'speed': '慢',
        'duration': '约30秒',
        'text': "A: Good morning! What can I get for you today?\nB: I'd like a medium latte, please. With oat milk if you have it.\nA: Sure! Would you like anything to eat with that?\nB: Just a croissant, please. To go.\nA: That'll be $8.50. Card or cash?\nB: Card, please. Contactless is fine.",
        'vocab': ['oat milk（燕麦奶）', 'croissant（可颂/牛角包）', 'to go（带走）', 'contactless（免接触支付）'],
        'tags': ['日常场景', '初级']
    },
    {
        'level': 2,
        'level_text': 'Level 2 · 进阶',
        'difficulty': '★★☆☆☆',
        'title': 'Handling a Customer Complaint',
        'speed': '中等',
        'duration': '约1分钟',
        'text': "A: I'm calling about the shipment we received yesterday. About 10% of the items are damaged.\nB: Oh, I'm really sorry to hear that. Can you send me some photos of the damaged items?\nA: Sure, I'll email them right away. What's the next step?\nB: Once I see the photos, I'll arrange a replacement shipment immediately. No extra charge, of course.\nA: Thank you. I appreciate the quick response.\nB: Not at all. We take quality issues very seriously. You'll have the replacements within a week.",
        'vocab': ['shipment（货物/装运）', 'damaged（损坏的）', 'replacement（替换品）', 'take seriously（认真对待）'],
        'tags': ['客户投诉', '中级']
    }
]

def get_daily_fashion():
    """穿搭灵感 - 根据日期轮换"""
    today = datetime.now()
    idx = today.timetuple().tm_yday % len(FASHION_LOOKS)
    return FASHION_LOOKS[idx]

FASHION_LOOKS = [
    {
        'color_tip': {
            'title': '今日色彩搭配：奶油黄 × 雾霾蓝',
            'desc': '橄榄皮超友好的配色！奶油黄温暖柔和衬肤色，雾霾蓝低饱和度显白不挑人。',
            'formula': '奶油黄上衣 + 雾霾蓝直筒牛仔裤 + 米白色单鞋',
            'colors': ['#F7E8A0', '#B0C8D8', '#F5F0E0', '#D4A574'],
            'color_names': ['奶油黄', '雾霾蓝', '米白', '浅棕']
        },
        'looks': [
            {
                'title': '一字肩针织上衣 + 直筒牛仔半裙',
                'top': {'emoji': '🧶', 'desc': '浅粉色一字肩针织衫，露锁骨不露手臂，袖口微喇修饰'},
                'bottom': {'emoji': '👖', 'desc': '浅蓝直筒牛仔半裙，中长款过膝，前开衩设计'},
                'tips': '一字肩拉长颈部线条，浅粉色衬橄榄皮；直筒牛仔半裙修饰胯部不紧绷；搭配3cm中跟米色凉鞋。',
                'tags': ['一字肩', '牛仔半裙', '小个子'],
                'search_url': 'https://www.xiaohongshu.com/search_result?keyword=一字肩针织+直筒牛仔半裙+小个子'
            },
            {
                'title': 'V领收腰连衣裙 + 短款开衫',
                'top': {'emoji': '👗', 'desc': '雾霾蓝V领收腰连衣裙，A字微摆不蓬松，七分袖遮手臂'},
                'bottom': {'emoji': '🧥', 'desc': '米白色短款针织开衫，长度到腰线以上，强调高腰比例'},
                'tips': 'V领显脸小、延伸颈部；收腰突出细腰优势；短开衫提高腰线，158cm也能穿出好比例！',
                'tags': ['V领', '收腰裙', '开衫搭配'],
                'search_url': 'https://www.xiaohongshu.com/search_result?keyword=V领收腰连衣裙+小个子+梨型'
            }
        ],
        'shoes': {
            'items': [
                '👡 米白色方头中跟凉鞋（跟高4cm）- 百搭色，粗跟好走不累',
                '👠 裸粉色尖头中跟单鞋（跟高4.5cm）- 延伸脚背显腿长',
                '🥿 编织坡跟凉拖（跟高3.5cm）- 休闲精致有呼吸感'
            ],
            'tip': '小个子选鞋：尖头>圆头；裸色>深色；露脚背>全包裹；粗跟3-5cm最舒适'
        }
    },
    {
        'color_tip': {
            'title': '今日色彩搭配：薄荷绿 × 米杏色',
            'desc': '清新减龄配色！薄荷绿温柔清爽，米杏色柔和温暖，两个低饱和色叠加超级显白。',
            'formula': '薄荷绿衬衫 + 米杏色阔腿裤 + 白色乐福鞋',
            'colors': ['#B5D8C8', '#F0E4D0', '#FFFFFF', '#D4A574'],
            'color_names': ['薄荷绿', '米杏色', '白色', '浅棕']
        },
        'looks': [
            {
                'title': '圆领真丝衬衫 + 垂感阔腿裤',
                'top': {'emoji': '👔', 'desc': '香槟色圆领真丝衬衫，微泡泡袖修饰手臂，光泽感提气色'},
                'bottom': {'emoji': '👖', 'desc': '奶油白垂感阔腿裤，高腰设计，不贴腿修饰胯部'},
                'tips': '圆领露出锁骨，香槟色光泽感衬橄榄皮超显白！垂感阔腿裤遮胯显瘦，搭配5cm粗跟凉鞋。',
                'tags': ['阔腿裤', '真丝衬衫', '商务穿搭'],
                'search_url': 'https://www.douyin.com/search/小个子梨型身材+阔腿裤穿搭'
            },
            {
                'title': '一字肩碎花上衣 + 高腰A字半裙',
                'top': {'emoji': '🌸', 'desc': '鹅黄色一字肩碎花上衣，松紧领口两穿，微泡泡袖'},
                'bottom': {'emoji': '👗', 'desc': '白色高腰A字半裙，挺括棉质面料，非纱质不蓬松'},
                'tips': '鹅黄色是橄榄皮的本命色！一字肩两穿，A字半裙材质挺括，搭配编织凉鞋（3cm跟）。',
                'tags': ['碎花', 'A字裙', '约会穿搭'],
                'search_url': 'https://www.xiaohongshu.com/search_result?keyword=鹅黄色一字肩+梨型身材+小个子'
            }
        ],
        'shoes': {
            'items': [
                '👡 杏色方头粗跟凉鞋（跟高4cm）- 温柔百搭',
                '👠 白色尖头穆勒鞋（跟高3.5cm）- 慵懒精致',
                '🥿 裸粉色芭蕾平底鞋（内增高2cm）- 舒适显高'
            ],
            'tip': '小个子选鞋：尖头>圆头；裸色>深色；露脚背>全包裹；粗跟3-5cm最舒适'
        }
    },
    {
        'color_tip': {
            'title': '今日色彩搭配：香芋紫 × 燕麦白',
            'desc': '温柔高级感配色！香芋紫温柔不张扬，燕麦白中和紫色的甜腻感，橄榄皮穿紫色意外显白。',
            'formula': '香芋紫针织开衫 + 燕麦白A字半裙 + 裸色尖头鞋',
            'colors': ['#C8B8D8', '#E8DCC8', '#F5F0E8', '#D4A0A0'],
            'color_names': ['香芋紫', '燕麦白', '奶白', '裸粉']
        },
        'looks': [
            {
                'title': 'V领针织开衫 + A字牛仔半裙',
                'top': {'emoji': '🧶', 'desc': '浅紫色V领针织开衫，五分袖修饰手臂，下摆塞进裙子里'},
                'bottom': {'emoji': '👗', 'desc': '浅蓝A字牛仔半裙，前开衩，中长款，挺括不蓬松'},
                'tips': 'V领延伸颈部，浅紫色意外显白；A字牛仔裙板正有型，前开衩走路方便。搭配白色尖头鞋。',
                'tags': ['V领', 'A字裙', '温柔风'],
                'search_url': 'https://www.xiaohongshu.com/search_result?keyword=紫色开衫+牛仔半裙+小个子'
            },
            {
                'title': '方领泡泡袖上衣 + 高腰阔腿裤',
                'top': {'emoji': '👚', 'desc': '白色方领泡泡袖上衣，大方领露锁骨，微泡泡袖遮手臂'},
                'bottom': {'emoji': '👖', 'desc': '浅卡其高腰阔腿裤，垂坠面料，不贴腿遮胯显瘦'},
                'tips': '方领显锁骨和天鹅颈，泡泡袖量感刚好遮手臂不显壮；阔腿裤高腰设计拉长比例。',
                'tags': ['方领', '阔腿裤', '通勤穿搭'],
                'search_url': 'https://www.xiaohongshu.com/search_result?keyword=方领上衣+阔腿裤+梨型+小个子'
            }
        ],
        'shoes': {
            'items': [
                '👠 白色尖头中跟单鞋（跟高5cm）- 气场拉满',
                '👡 裸色一字带粗跟凉鞋（跟高4cm）- 精致百搭',
                '🥿 米色尖头平底鞋（内增高2.5cm）- 舒适通勤'
            ],
            'tip': '小个子选鞋：尖头>圆头；裸色>深色；露脚背>全包裹；粗跟3-5cm最舒适'
        }
    }
]

# ===== 主流程 =====
def main():
    print(f"🪔 芝麻油工作台 - 每日内容抓取")
    print(f"📅 运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    data = {
        'updateTime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'updateDate': datetime.now().strftime('%Y年%m月%d日'),
        'weekDay': ['一', '二', '三', '四', '五', '六', '日'][datetime.now().weekday()],
        'tech': fetch_tech_finance(),
        'trade': fetch_trade_news(),
        'speaking': fetch_speaking(),
        'listening': fetch_listening(),
        'fashion': fetch_fashion(),
        'blog': fetch_blog()
    }
    
    # 写入 JSON
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 数据已保存至: {OUTPUT_FILE}")
    print(f"📦 文件大小: {os.path.getsize(OUTPUT_FILE)} bytes")

if __name__ == '__main__':
    main()
