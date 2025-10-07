#!/usr/bin/env python3
"""
生成 eBird 国家和地区数据的脚本
一次性从 eBird API 获取所有国家和地区信息，保存为 JSON 文件
"""
import json
import time
from ebird_country_filter import eBirdCountryFilter
import os

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

        country_data = {
            "code": country_code,
            "name": country_name,
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
