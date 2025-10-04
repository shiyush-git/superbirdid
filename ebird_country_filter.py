#!/usr/bin/env python3
"""
eBird国家鸟类过滤器
使用eBird API获取特定国家的鸟类列表，并缓存结果以提高效率
"""
import requests
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set
import time

class eBirdCountryFilter:
    def __init__(self, api_key: str, cache_dir: str = "ebird_cache", offline_dir: str = "offline_ebird_data"):
        """
        初始化eBird国家过滤器

        Args:
            api_key: eBird API密钥
            cache_dir: 缓存目录路径
            offline_dir: 离线数据目录路径
        """
        self.api_key = api_key
        self.cache_dir = cache_dir
        self.offline_dir = offline_dir
        self.base_url = "https://api.ebird.org/v2"
        self.headers = {
            'x-ebirdapitoken': api_key
        }

        # 确保缓存目录存在
        os.makedirs(cache_dir, exist_ok=True)

        # 确保离线数据目录存在
        os.makedirs(offline_dir, exist_ok=True)

        # 缓存有效期（天数）
        self.cache_validity_days = 30
        
        # 国家代码映射（ISO 2字母代码）
        self.country_codes = {
            'australia': 'AU',
            'china': 'CN', 
            'usa': 'US',
            'canada': 'CA',
            'brazil': 'BR',
            'india': 'IN',
            'indonesia': 'ID',
            'mexico': 'MX',
            'colombia': 'CO',
            'peru': 'PE',
            'ecuador': 'EC',
            'bolivia': 'BO',
            'venezuela': 'VE',
            'chile': 'CL',
            'argentina': 'AR',
            'south_africa': 'ZA',
            'kenya': 'KE',
            'tanzania': 'TZ',
            'madagascar': 'MG',
            'cameroon': 'CM',
            'ghana': 'GH',
            'nigeria': 'NG',
            'ethiopia': 'ET',
            'uganda': 'UG',
            'costa_rica': 'CR',
            'panama': 'PA',
            'guatemala': 'GT',
            'nicaragua': 'NI',
            'honduras': 'HN',
            'belize': 'BZ',
            'el_salvador': 'SV',
            'norway': 'NO',
            'sweden': 'SE',
            'finland': 'FI',
            'united_kingdom': 'GB',
            'france': 'FR',
            'spain': 'ES',
            'italy': 'IT',
            'germany': 'DE',
            'poland': 'PL',
            'romania': 'RO',
            'turkey': 'TR',
            'russia': 'RU',
            'japan': 'JP',
            'south_korea': 'KR',
            'thailand': 'TH',
            'vietnam': 'VN',
            'philippines': 'PH',
            'malaysia': 'MY',
            'singapore': 'SG',
            'new_zealand': 'NZ'
        }
    
    def get_cache_file_path(self, country_code: str) -> str:
        """获取缓存文件路径"""
        return os.path.join(self.cache_dir, f"species_list_{country_code}.json")
    
    def is_cache_valid(self, cache_file: str) -> bool:
        """检查缓存是否有效"""
        if not os.path.exists(cache_file):
            return False
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # 检查缓存时间
            cache_time = datetime.fromisoformat(cache_data.get('cached_at', '1970-01-01'))
            expiry_time = cache_time + timedelta(days=self.cache_validity_days)
            
            return datetime.now() < expiry_time
        except:
            return False
    
    def load_cached_species_list(self, country_code: str) -> Optional[Set[str]]:
        """从缓存加载物种列表"""
        cache_file = self.get_cache_file_path(country_code)

        if not self.is_cache_valid(cache_file):
            return None

        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)

            species_set = set(cache_data.get('species', []))
            print(f"从缓存加载 {country_code} 的物种列表: {len(species_set)} 个物种")
            return species_set
        except Exception as e:
            print(f"加载缓存失败: {e}")
            return None

    def load_offline_species_list(self, country_code: str) -> Optional[Set[str]]:
        """从离线数据加载物种列表"""
        offline_file = os.path.join(self.offline_dir, f"species_list_{country_code}.json")

        if not os.path.exists(offline_file):
            return None

        try:
            with open(offline_file, 'r', encoding='utf-8') as f:
                offline_data = json.load(f)

            species_set = set(offline_data.get('species', []))
            print(f"从离线数据加载 {country_code} 的物种列表: {len(species_set)} 个物种 (离线)")
            return species_set
        except Exception as e:
            print(f"加载离线数据失败: {e}")
            return None

    def is_offline_data_available(self) -> bool:
        """检查是否有离线数据可用"""
        index_file = os.path.join(self.offline_dir, "offline_index.json")
        return os.path.exists(index_file)

    def get_available_offline_countries(self) -> List[str]:
        """获取可用的离线国家列表"""
        if not self.is_offline_data_available():
            return []

        try:
            index_file = os.path.join(self.offline_dir, "offline_index.json")
            with open(index_file, 'r', encoding='utf-8') as f:
                index_data = json.load(f)

            return list(index_data.get('countries', {}).keys())
        except Exception as e:
            print(f"读取离线数据索引失败: {e}")
            return []
    
    def save_species_list_to_cache(self, country_code: str, species_list: List[str]) -> None:
        """保存物种列表到缓存"""
        cache_file = self.get_cache_file_path(country_code)
        
        cache_data = {
            'country_code': country_code,
            'species': list(species_list),
            'species_count': len(species_list),
            'cached_at': datetime.now().isoformat(),
            'api_version': '2.0'
        }
        
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            print(f"已缓存 {country_code} 的物种列表: {len(species_list)} 个物种")
        except Exception as e:
            print(f"保存缓存失败: {e}")
    
    def fetch_species_list_from_api(self, country_code: str) -> Optional[List[str]]:
        """从eBird API获取物种列表"""
        url = f"{self.base_url}/product/spplist/{country_code}"

        try:
            print(f"正在从eBird API获取 {country_code} 的物种列表...")
            response = requests.get(url, headers=self.headers, timeout=30)

            if response.status_code == 200:
                species_list = response.json()
                print(f"成功获取 {country_code} 的 {len(species_list)} 个物种")

                # 添加短暂延迟以避免API限制
                time.sleep(0.1)

                return species_list
            elif response.status_code == 404:
                print(f"国家代码 {country_code} 未找到")
                return None
            elif response.status_code == 429:
                print("API请求限制，请稍后再试")
                return None
            else:
                print(f"API请求失败: {response.status_code}")
                return None

        except requests.exceptions.RequestException as e:
            print(f"网络请求失败: {e}")
            return None

    def get_location_cache_file_path(self, lat: float, lon: float, radius: int) -> str:
        """获取位置缓存文件路径"""
        # 使用坐标和半径创建唯一的缓存文件名
        lat_str = f"{lat:.3f}".replace('.', '_').replace('-', 'n')
        lon_str = f"{lon:.3f}".replace('.', '_').replace('-', 'n')
        return os.path.join(self.cache_dir, f"location_{lat_str}_{lon_str}_{radius}km.json")

    def fetch_species_list_by_location(self, lat: float, lon: float, radius: int = 25) -> Optional[List[str]]:
        """
        基于GPS坐标从eBird API获取附近区域的物种列表

        Args:
            lat: 纬度
            lon: 经度
            radius: 搜索半径（公里，最大50km）

        Returns:
            物种代码列表，如果获取失败返回None
        """
        # 限制半径范围
        radius = min(max(radius, 1), 50)

        # 使用eBird的近期观察记录API（最近30天）
        url = f"{self.base_url}/data/obs/geo/recent"

        params = {
            'lat': lat,
            'lng': lon,
            'dist': radius,
            'back': 30,  # 最近30天的记录
            'maxResults': 10000,  # 获取更多结果
            'includeProvisional': 'false',  # 只包含审核通过的记录
            'fmt': 'json'
        }

        try:
            print(f"正在获取位置 ({lat:.3f}, {lon:.3f}) 半径 {radius}km 内的鸟类观察记录...")
            response = requests.get(url, headers=self.headers, params=params, timeout=30)

            if response.status_code == 200:
                observations = response.json()

                # 提取唯一的物种代码
                species_codes = list(set(obs['speciesCode'] for obs in observations))

                print(f"成功获取 {len(species_codes)} 个物种（基于 {len(observations)} 条观察记录）")

                # 添加短暂延迟以避免API限制
                time.sleep(0.1)

                return species_codes
            elif response.status_code == 404:
                print(f"位置 ({lat}, {lon}) 未找到观察记录")
                return None
            elif response.status_code == 429:
                print("API请求限制，请稍后再试")
                return None
            else:
                print(f"API请求失败: {response.status_code}")
                return None

        except requests.exceptions.RequestException as e:
            print(f"网络请求失败: {e}")
            return None

    def get_location_species_list(self, lat: float, lon: float, radius: int = 25) -> Optional[Set[str]]:
        """
        获取GPS位置附近的鸟类物种列表（优先从缓存加载）

        Args:
            lat: 纬度
            lon: 经度
            radius: 搜索半径（公里）

        Returns:
            物种代码集合，如果获取失败返回None
        """
        # 检查缓存
        cache_file = self.get_location_cache_file_path(lat, lon, radius)

        if self.is_cache_valid(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)

                species_set = set(cache_data.get('species', []))
                print(f"从缓存加载位置物种列表: {len(species_set)} 个物种")
                return species_set
            except Exception as e:
                print(f"加载位置缓存失败: {e}")

        # 缓存无效或不存在，从API获取
        species_list = self.fetch_species_list_by_location(lat, lon, radius)

        if species_list:
            # 保存到缓存
            cache_data = {
                'lat': lat,
                'lon': lon,
                'radius': radius,
                'species': species_list,
                'species_count': len(species_list),
                'cached_at': datetime.now().isoformat(),
                'api_version': '2.0'
            }

            try:
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(cache_data, f, ensure_ascii=False, indent=2)
                print(f"已缓存位置物种列表: {len(species_list)} 个物种")
            except Exception as e:
                print(f"保存位置缓存失败: {e}")

            return set(species_list)

        return None
    
    def get_country_species_list(self, country_input: str) -> Optional[Set[str]]:
        """
        获取国家的鸟类物种列表（优先级：缓存 > API > 离线数据）

        Args:
            country_input: 国家名称或代码

        Returns:
            物种代码集合，如果获取失败返回None
        """
        # 标准化国家输入
        country_input = country_input.lower().strip()

        # 尝试直接作为国家代码使用
        country_code = country_input.upper()

        # 如果不是2位代码，尝试从映射中查找
        if len(country_code) != 2 or not country_code.isalpha():
            country_code = self.country_codes.get(country_input)

            if not country_code:
                # 尝试部分匹配
                for key, code in self.country_codes.items():
                    if country_input in key or key in country_input:
                        country_code = code
                        break

        if not country_code:
            print(f"未找到国家代码: {country_input}")
            print("支持的国家:")
            for name, code in list(self.country_codes.items())[:10]:
                print(f"  {name}: {code}")
            print("  ... 等更多国家")
            return None

        # 1. 首先尝试从缓存加载
        cached_species = self.load_cached_species_list(country_code)
        if cached_species is not None:
            return cached_species

        # 2. 缓存无效，尝试从API获取
        species_list = self.fetch_species_list_from_api(country_code)

        if species_list:
            # 保存到缓存
            self.save_species_list_to_cache(country_code, species_list)
            return set(species_list)

        # 3. API失败，尝试从离线数据加载
        print(f"API获取失败，尝试使用离线数据...")
        offline_species = self.load_offline_species_list(country_code)
        if offline_species is not None:
            return offline_species

        print(f"❌ 无法获取 {country_code} 的鸟类数据（尝试了缓存、API和离线数据）")
        return None
    
    def filter_results_by_country(self, recognition_results: List[Dict], country_species: Set[str]) -> List[Dict]:
        """
        使用国家物种列表过滤识别结果
        
        Args:
            recognition_results: 鸟类识别结果列表
            country_species: 国家物种代码集合
            
        Returns:
            过滤后的结果列表
        """
        filtered_results = []
        
        for result in recognition_results:
            # 假设结果中包含物种的eBird代码
            # 这需要根据实际的识别结果格式调整
            species_code = result.get('ebird_code') or result.get('species_code')
            
            if not species_code:
                # 如果没有eBird代码，尝试从英文名称推断
                english_name = result.get('english_name', '')
                if english_name:
                    # 这里需要实现英文名称到eBird代码的映射
                    # 或者使用其他方法匹配
                    pass
            
            # 检查物种是否在国家列表中
            if species_code and species_code in country_species:
                result['country_match'] = True
                result['confidence_boost'] = 1.2  # 给予20%的置信度提升
                filtered_results.append(result)
            elif not species_code:
                # 如果无法确定物种代码，保留但不提升
                result['country_match'] = False
                filtered_results.append(result)
        
        # 按照是否匹配国家和置信度排序
        filtered_results.sort(
            key=lambda x: (x.get('country_match', False), x.get('confidence', 0)), 
            reverse=True
        )
        
        return filtered_results
    
    def get_supported_countries(self) -> Dict[str, str]:
        """获取支持的国家列表"""
        return self.country_codes.copy()
    
    def clear_cache(self, country_code: str = None) -> None:
        """清理缓存"""
        if country_code:
            cache_file = self.get_cache_file_path(country_code)
            if os.path.exists(cache_file):
                os.remove(cache_file)
                print(f"已清理 {country_code} 的缓存")
        else:
            # 清理所有缓存
            for file in os.listdir(self.cache_dir):
                if file.startswith('species_list_') and file.endswith('.json'):
                    os.remove(os.path.join(self.cache_dir, file))
            print("已清理所有缓存")


def test_ebird_filter():
    """测试eBird过滤器"""
    # 使用你提供的API密钥
    api_key = "60nan25sogpo"
    filter_system = eBirdCountryFilter(api_key)
    
    # 测试获取澳洲鸟类列表
    print("=== 测试澳洲鸟类列表 ===")
    au_species = filter_system.get_country_species_list("australia")
    if au_species:
        print(f"澳洲鸟类物种数量: {len(au_species)}")
        print("前10个物种代码:", list(au_species)[:10])
    
    # 测试获取中国鸟类列表
    print("\n=== 测试中国鸟类列表 ===")
    cn_species = filter_system.get_country_species_list("china")
    if cn_species:
        print(f"中国鸟类物种数量: {len(cn_species)}")
        print("前10个物种代码:", list(cn_species)[:10])


if __name__ == "__main__":
    test_ebird_filter()