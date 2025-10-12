#!/usr/bin/env python3
"""
生成 eBird 国家和地区数据的脚本
一次性从 eBird API 获取所有国家和地区信息，保存为 JSON 文件
"""
import json
import time
from ebird_country_filter import eBirdCountryFilter
import os

# 国家代码到中文名称的映射（完整版）
COUNTRY_NAMES_CN = {
    # 最常用国家
    'AU': '澳大利亚', 'US': '美国', 'CN': '中国', 'GB': '英国', 'CA': '加拿大',
    'TW': '台湾', 'HK': '香港', 'MO': '澳门',

    # 鸟类资源丰富的国家
    'BR': '巴西', 'CO': '哥伦比亚', 'PE': '秘鲁', 'EC': '厄瓜多尔', 'IN': '印度',
    'ID': '印度尼西亚', 'MX': '墨西哥', 'VE': '委内瑞拉', 'BO': '玻利维亚',

    # 亚洲国家
    'JP': '日本', 'KR': '韩国', 'TH': '泰国', 'VN': '越南', 'PH': '菲律宾',
    'MY': '马来西亚', 'SG': '新加坡', 'MM': '缅甸', 'KH': '柬埔寨', 'LA': '老挝',
    'NP': '尼泊尔', 'BT': '不丹', 'BD': '孟加拉国', 'LK': '斯里兰卡', 'PK': '巴基斯坦',
    'KZ': '哈萨克斯坦', 'UZ': '乌兹别克斯坦', 'KG': '吉尔吉斯斯坦', 'TJ': '塔吉克斯坦',
    'TM': '土库曼斯坦', 'MN': '蒙古', 'KP': '朝鲜', 'BN': '文莱', 'TL': '东帝汶',

    # 欧洲国家
    'FR': '法国', 'DE': '德国', 'IT': '意大利', 'ES': '西班牙', 'NL': '荷兰',
    'BE': '比利时', 'CH': '瑞士', 'AT': '奥地利', 'PL': '波兰', 'SE': '瑞典',
    'NO': '挪威', 'FI': '芬兰', 'DK': '丹麦', 'GR': '希腊', 'PT': '葡萄牙',
    'CZ': '捷克', 'HU': '匈牙利', 'RO': '罗马尼亚', 'BG': '保加利亚', 'SK': '斯洛伐克',
    'HR': '克罗地亚', 'SI': '斯洛文尼亚', 'LT': '立陶宛', 'LV': '拉脱维亚', 'EE': '爱沙尼亚',
    'IE': '爱尔兰', 'IS': '冰岛', 'LU': '卢森堡', 'MT': '马耳他', 'CY': '塞浦路斯',
    'RS': '塞尔维亚', 'BA': '波黑', 'ME': '黑山', 'MK': '北马其顿', 'AL': '阿尔巴尼亚',
    'BY': '白俄罗斯', 'UA': '乌克兰', 'MD': '摩尔多瓦', 'RU': '俄罗斯',

    # 南美洲国家
    'AR': '阿根廷', 'CL': '智利', 'UY': '乌拉圭', 'PY': '巴拉圭', 'GY': '圭亚那',
    'SR': '苏里南', 'GF': '法属圭亚那',

    # 中美洲及加勒比国家
    'CR': '哥斯达黎加', 'PA': '巴拿马', 'GT': '危地马拉', 'HN': '洪都拉斯',
    'NI': '尼加拉瓜', 'SV': '萨尔瓦多', 'BZ': '伯利兹', 'CU': '古巴',
    'JM': '牙买加', 'HT': '海地', 'DO': '多米尼加', 'TT': '特立尼达和多巴哥',

    # 非洲国家
    'ZA': '南非', 'KE': '肯尼亚', 'TZ': '坦桑尼亚', 'UG': '乌干达', 'ET': '埃塞俄比亚',
    'MG': '马达加斯加', 'CM': '喀麦隆', 'GH': '加纳', 'NG': '尼日利亚', 'SN': '塞内加尔',
    'CI': '科特迪瓦', 'MA': '摩洛哥', 'DZ': '阿尔及利亚', 'TN': '突尼斯', 'EG': '埃及',
    'BW': '博茨瓦纳', 'NA': '纳米比亚', 'ZM': '赞比亚', 'ZW': '津巴布韦', 'MZ': '莫桑比克',
    'AO': '安哥拉', 'RW': '卢旺达', 'BI': '布隆迪', 'MW': '马拉维', 'LS': '莱索托',
    'SZ': '斯威士兰', 'GA': '加蓬', 'CG': '刚果(布)', 'CD': '刚果(金)', 'CF': '中非',
    'TD': '乍得', 'NE': '尼日尔', 'ML': '马里', 'BF': '布基纳法索', 'MR': '毛里塔尼亚',
    'GM': '冈比亚', 'GN': '几内亚', 'SL': '塞拉利昂', 'LR': '利比里亚', 'BJ': '贝宁',
    'TG': '多哥', 'ER': '厄立特里亚', 'DJ': '吉布提', 'SO': '索马里', 'SS': '南苏丹',
    'SD': '苏丹', 'LY': '利比亚', 'EH': '西撒哈拉',

    # 大洋洲国家
    'NZ': '新西兰', 'PG': '巴布亚新几内亚', 'FJ': '斐济', 'SB': '所罗门群岛',
    'VU': '瓦努阿图', 'NC': '新喀里多尼亚', 'PF': '法属波利尼西亚', 'WS': '萨摩亚',
    'TO': '汤加', 'KI': '基里巴斯', 'FM': '密克罗尼西亚', 'PW': '帕劳', 'MH': '马绍尔群岛',

    # 中东国家
    'TR': '土耳其', 'IL': '以列', 'SA': '沙特阿拉伯', 'AE': '阿联酋', 'IQ': '伊拉克',
    'IR': '伊朗', 'JO': '约旦', 'LB': '黎巴嫩', 'SY': '叙利亚', 'YE': '也门',
    'OM': '阿曼', 'KW': '科威特', 'BH': '巴林', 'QA': '卡塔尔', 'PS': '巴勒斯坦',
    'AM': '亚美尼亚', 'AZ': '阿塞拜疆', 'GE': '格鲁吉亚',

    # 其他地区
    'GI': '直布罗陀', 'FO': '法罗群岛', 'GL': '格陵兰', 'AQ': '南极洲',
}

# 优先级排序：定义国家显示顺序
PRIORITY_ORDER = [
    # 第一梯队：最常用的主要国家（5个）
    'AU', 'US', 'CN', 'GB', 'CA',

    # 第二梯队：港澳台（3个）
    'TW', 'HK', 'MO',

    # 第三梯队：鸟类资源最丰富的国家（按鸟种数量排序，约15个）
    'BR',  # 巴西 ~1900种
    'CO',  # 哥伦比亚 ~1900种
    'PE',  # 秘鲁 ~1850种
    'EC',  # 厄瓜多尔 ~1650种
    'IN',  # 印度 ~1300种
    'ID',  # 印度尼西亚 ~1700种
    'MX',  # 墨西哥 ~1100种
    'VE',  # 委内瑞拉 ~1400种
    'BO',  # 玻利维亚 ~1400种
    'AR',  # 阿根廷 ~1000种
    'ZA',  # 南非 ~860种
    'KE',  # 肯尼亚 ~1100种
    'TZ',  # 坦桑尼亚 ~1100种
    'PG',  # 巴布亚新几内亚 ~780种
    'MG',  # 马达加斯加 ~280种（特有种多）

    # 第四梯队：其他常用观鸟国家（按地区分组，约20个）
    # 亚洲
    'JP', 'KR', 'TH', 'VN', 'PH', 'MY', 'SG', 'NP',
    # 欧洲
    'FR', 'DE', 'ES', 'IT', 'NL', 'NO', 'SE', 'FI',
    # 美洲
    'CR', 'PA', 'CL', 'NZ',
]

def get_country_sort_key(country):
    """
    获取国家排序键

    返回元组: (优先级, 中文名或英文名)
    - 优先级越小越靠前
    - 同优先级按名称字母顺序
    """
    code = country['code']

    # 检查是否在优先级列表中
    if code in PRIORITY_ORDER:
        priority = PRIORITY_ORDER.index(code)
    else:
        # 不在优先级列表中的国家，排在后面
        priority = 9999

    # 使用中文名或英文名作为次要排序，确保不为 None
    name = country.get('name_cn') or country.get('name', '')

    return (priority, name)

def generate_regions_data(quick_mode=False):
    """
    生成完整的国家和地区数据

    Args:
        quick_mode: 如果为True，只生成常用国家的数据（约30个），快速模式约需1分钟
                   如果为False，生成全部253个国家，完整模式约需10-15分钟
    """
    api_key = os.environ.get('EBIRD_API_KEY', '60nan25sogpo')
    filter_system = eBirdCountryFilter(api_key)

    print("=" * 60)
    print("开始生成 eBird 国家和地区数据")
    if quick_mode:
        print("模式: 快速模式（仅常用国家）")
    else:
        print("模式: 完整模式（全部国家，需要10-15分钟）")
    print("=" * 60)

    # 1. 获取所有国家
    print("\n步骤 1/2: 获取全球国家列表...")
    all_countries = filter_system.get_all_countries()

    if not all_countries:
        print("❌ 获取国家列表失败")
        return

    # 如果是快速模式，只处理常用国家
    if quick_mode:
        # 常用国家代码列表
        priority_countries = [
            'AU', 'CN', 'US', 'CA', 'GB', 'IN', 'BR', 'MX', 'CO', 'PE',
            'EC', 'AR', 'CL', 'ZA', 'KE', 'TZ', 'JP', 'KR', 'TH', 'VN',
            'PH', 'MY', 'ID', 'SG', 'NZ', 'FR', 'ES', 'IT', 'DE', 'NO'
        ]
        countries = [c for c in all_countries if c['code'] in priority_countries]
        print(f"✓ 快速模式: 处理 {len(countries)} 个常用国家（总共 {len(all_countries)} 个）")
    else:
        countries = all_countries
        print(f"✓ 完整模式: 处理全部 {len(countries)} 个国家/地区")

    # 2. 为每个国家获取二级区域
    print("\n步骤 2/2: 获取每个国家的二级区域...")

    regions_data = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_countries": len(countries),
        "countries": []
    }

    failed_countries = []

    for i, country in enumerate(countries, 1):
        country_code = country['code']
        country_name = country['name']

        print(f"\n[{i}/{len(countries)}] {country_code} - {country_name}")

        # 获取该国家的二级区域
        subnational_regions = filter_system.get_subnational_regions(country_code)

        if subnational_regions is None:
            # API 调用失败
            print(f"  ⚠️ API 调用失败，跳过")
            failed_countries.append(country_code)
            time.sleep(0.5)  # 失败后等待长一点
            continue

        # 添加中文名称
        country_name_cn = COUNTRY_NAMES_CN.get(country_code)

        country_data = {
            "code": country_code,
            "name": country_name,
            "name_cn": country_name_cn,  # 可能为 None
            "has_regions": len(subnational_regions) > 0,
            "regions_count": len(subnational_regions),
            "regions": subnational_regions
        }

        regions_data["countries"].append(country_data)

        if len(subnational_regions) > 0:
            print(f"  ✓ 包含 {len(subnational_regions)} 个二级区域")
        else:
            print(f"  - 无二级区域")

        # 避免 API 限制，每次请求后等待
        time.sleep(0.2)

    # 2.5. 对国家列表进行排序
    print("\n对国家列表进行排序...")
    regions_data["countries"].sort(key=get_country_sort_key)
    print(f"✓ 排序完成，前10个国家: {', '.join([c['code'] for c in regions_data['countries'][:10]])}")

    # 3. 保存到文件
    output_file = "ebird_regions.json"
    print(f"\n步骤 3/3: 保存到文件 {output_file}...")

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(regions_data, f, ensure_ascii=False, indent=2)

    print(f"✓ 数据已保存到 {output_file}")

    # 4. 统计信息
    print("\n" + "=" * 60)
    print("生成完成！统计信息：")
    print("=" * 60)
    print(f"总国家数: {len(regions_data['countries'])}")

    countries_with_regions = sum(1 for c in regions_data['countries'] if c['has_regions'])
    print(f"有二级区域的国家: {countries_with_regions}")

    total_regions = sum(c['regions_count'] for c in regions_data['countries'])
    print(f"二级区域总数: {total_regions}")

    if failed_countries:
        print(f"\n⚠️ 获取失败的国家 ({len(failed_countries)}): {', '.join(failed_countries)}")

    # 5. 显示一些示例
    print("\n示例数据（前5个有二级区域的国家）：")
    count = 0
    for country in regions_data['countries']:
        if country['has_regions'] and count < 5:
            print(f"\n{country['code']} - {country['name']} ({country['regions_count']} 个区域)")
            for region in country['regions'][:3]:
                print(f"  - {region['code']}: {region['name']}")
            if country['regions_count'] > 3:
                print(f"  ... 还有 {country['regions_count'] - 3} 个")
            count += 1

if __name__ == "__main__":
    import sys

    # 默认使用快速模式，如果需要完整模式，运行: python3 generate_regions_data.py --full
    quick_mode = "--full" not in sys.argv

    generate_regions_data(quick_mode=quick_mode)
