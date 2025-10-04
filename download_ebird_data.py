#!/usr/bin/env python3
"""
批量下载eBird国家鸟种数据脚本
下载主要国家的鸟种列表，用作离线备用数据
"""

import os
import json
import time
from datetime import datetime
from ebird_country_filter import eBirdCountryFilter

def download_country_data():
    """批量下载主要国家的eBird鸟种数据"""

    # 使用API密钥
    api_key = "60nan25sogpo"
    filter_system = eBirdCountryFilter(api_key, cache_dir="offline_ebird_data")

    # 优先下载的国家列表（按鸟类观鸟热门程度排序）
    priority_countries = [
        'australia', 'usa', 'canada', 'brazil', 'colombia', 'peru', 'ecuador',
        'costa_rica', 'south_africa', 'india', 'china', 'indonesia', 'philippines',
        'mexico', 'argentina', 'chile', 'bolivia', 'venezuela', 'panama',
        'kenya', 'tanzania', 'uganda', 'madagascar', 'cameroon', 'ghana',
        'united_kingdom', 'spain', 'france', 'germany', 'italy', 'norway',
        'sweden', 'finland', 'poland', 'romania', 'turkey', 'russia',
        'japan', 'south_korea', 'thailand', 'vietnam', 'malaysia', 'singapore',
        'new_zealand', 'guatemala', 'nicaragua', 'honduras', 'belize',
        'el_salvador', 'ethiopia', 'nigeria'
    ]

    print(f"🌍 开始批量下载 {len(priority_countries)} 个国家的eBird鸟种数据")
    print(f"📂 数据保存目录: offline_ebird_data/")
    print("=" * 60)

    successful_downloads = 0
    failed_downloads = []

    for i, country in enumerate(priority_countries, 1):
        print(f"\n[{i}/{len(priority_countries)}] 正在处理: {country}")

        try:
            # 尝试获取国家鸟种列表
            species_set = filter_system.get_country_species_list(country)

            if species_set and len(species_set) > 0:
                successful_downloads += 1
                print(f"✅ {country}: {len(species_set)} 个物种")
            else:
                failed_downloads.append(country)
                print(f"❌ {country}: 下载失败或无数据")

            # 添加延迟避免API限制
            time.sleep(0.5)

        except Exception as e:
            failed_downloads.append(country)
            print(f"❌ {country}: 异常 - {e}")
            time.sleep(1.0)  # 发生错误时等待更长时间

    # 下载总结
    print("\n" + "=" * 60)
    print("📊 下载总结:")
    print(f"✅ 成功下载: {successful_downloads} 个国家")
    print(f"❌ 下载失败: {len(failed_downloads)} 个国家")

    if failed_downloads:
        print("\n失败的国家:")
        for country in failed_downloads:
            print(f"  - {country}")

    # 生成离线数据索引文件
    create_offline_index()

    print(f"\n🎉 批量下载完成！")
    print(f"📁 离线数据可在 offline_ebird_data/ 目录中找到")

def create_offline_index():
    """创建离线数据索引文件"""
    offline_dir = "offline_ebird_data"
    index_file = os.path.join(offline_dir, "offline_index.json")

    if not os.path.exists(offline_dir):
        return

    index_data = {
        "created_at": datetime.now().isoformat(),
        "countries": {},
        "total_countries": 0,
        "total_species": 0
    }

    total_species_set = set()

    # 扫描所有缓存文件
    for filename in os.listdir(offline_dir):
        if filename.startswith("species_list_") and filename.endswith(".json"):
            country_code = filename.replace("species_list_", "").replace(".json", "")

            try:
                with open(os.path.join(offline_dir, filename), 'r', encoding='utf-8') as f:
                    country_data = json.load(f)

                species_list = country_data.get('species', [])
                species_count = len(species_list)

                index_data["countries"][country_code] = {
                    "species_count": species_count,
                    "cached_at": country_data.get('cached_at'),
                    "filename": filename
                }

                total_species_set.update(species_list)

            except Exception as e:
                print(f"⚠ 处理 {filename} 时出错: {e}")

    index_data["total_countries"] = len(index_data["countries"])
    index_data["total_species"] = len(total_species_set)

    # 保存索引文件
    try:
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, ensure_ascii=False, indent=2)

        print(f"📋 已创建离线数据索引: {index_file}")
        print(f"   - 包含 {index_data['total_countries']} 个国家")
        print(f"   - 总计 {index_data['total_species']} 个独特物种")

    except Exception as e:
        print(f"❌ 创建索引文件失败: {e}")

def show_offline_data_stats():
    """显示离线数据统计信息"""
    offline_dir = "offline_ebird_data"
    index_file = os.path.join(offline_dir, "offline_index.json")

    if not os.path.exists(index_file):
        print("❌ 没有找到离线数据索引文件")
        return

    try:
        with open(index_file, 'r', encoding='utf-8') as f:
            index_data = json.load(f)

        print("📊 离线eBird数据统计:")
        print(f"   创建时间: {index_data.get('created_at', 'Unknown')}")
        print(f"   国家数量: {index_data.get('total_countries', 0)}")
        print(f"   物种总数: {index_data.get('total_species', 0)}")
        print("\n各国物种数量 (前20个):")

        countries = index_data.get('countries', {})
        sorted_countries = sorted(countries.items(),
                                key=lambda x: x[1]['species_count'],
                                reverse=True)

        for i, (country_code, data) in enumerate(sorted_countries[:20], 1):
            species_count = data['species_count']
            print(f"   {i:2d}. {country_code}: {species_count:,} 物种")

    except Exception as e:
        print(f"❌ 读取索引文件失败: {e}")

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--stats":
        show_offline_data_stats()
    else:
        download_country_data()