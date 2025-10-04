#!/usr/bin/env python3
"""
英文鸟名到eBird代码的映射生成器
由于我们无法直接获得完整映射，这里提供一个基础的映射功能
"""
import re
from typing import Dict, Optional

class EnglishToEbirdMapper:
    def __init__(self):
        """初始化英文名到eBird代码的映射器"""
        # 一些常见的映射规则和已知的映射
        self.known_mappings = {
            # 澳洲常见鸟类
            'Australian Magpie': 'ausmag2',
            'Laughing Kookaburra': 'laukoo1', 
            'Rainbow Lorikeet': 'railoi',
            'Galah': 'galah',
            'Willie Wagtail': 'wilwag1',
            'Australian White Ibis': 'ausibo1',
            'Noisy Miner': 'noimyh1',
            'Pied Butcherbird': 'piebuv1',
            'Magpie-lark': 'maglat1',
            'Red Wattlebird': 'redwat1',
            
            # 中国常见鸟类
            'Oriental Magpie': 'ormagp1',
            'Eurasian Tree Sparrow': 'eutspa',
            'Red-billed Blue Magpie': 'rebmag1',
            'Azure-winged Magpie': 'azwmag1',
            'Light-vented Bulbul': 'livbul1',
            'Chinese Bulbul': 'chbbul1',
            'Eurasian Magpie': 'eurmagp',
            'Common Myna': 'commyn',
            'House Sparrow': 'houspa',
            'Rock Dove': 'rocpig',
            
            # 全球常见鸟类
            'House Sparrow': 'houspa',
            'Common Starling': 'eursta',
            'Rock Pigeon': 'rocpig', 
            'Barn Swallow': 'banswa',
            'House Finch': 'houfin',
            'American Robin': 'amerob',
            'Blue Jay': 'blujay',
            'Northern Cardinal': 'norcar',
            'Mourning Dove': 'moudov',
            'Red-winged Blackbird': 'rewbla',
        }
        
        # 预编译正则表达式用于名称清理
        self.clean_pattern = re.compile(r'[^\w\s-]')
    
    def clean_name(self, name: str) -> str:
        """清理鸟类名称"""
        if not name:
            return ""
        
        # 移除括号及其内容
        name = re.sub(r'\([^)]*\)', '', name)
        # 移除特殊字符，保留字母、数字、空格和连字符
        name = self.clean_pattern.sub('', name)
        # 标准化空格
        name = ' '.join(name.split())
        
        return name.strip()
    
    def name_to_ebird_code(self, english_name: str) -> Optional[str]:
        """
        尝试将英文名转换为eBird代码
        
        Args:
            english_name: 英文鸟类名称
            
        Returns:
            eBird代码（如果找到），否则返回None
        """
        if not english_name:
            return None
        
        # 清理名称
        clean_name = self.clean_name(english_name)
        
        # 首先检查已知映射
        if clean_name in self.known_mappings:
            return self.known_mappings[clean_name]
        
        # 尝试大小写不敏感匹配
        clean_lower = clean_name.lower()
        for known_name, code in self.known_mappings.items():
            if known_name.lower() == clean_lower:
                return code
        
        # 尝试部分匹配（包含关键词）
        for known_name, code in self.known_mappings.items():
            known_lower = known_name.lower()
            # 检查是否有共同的关键词
            clean_words = set(clean_lower.split())
            known_words = set(known_lower.split())
            
            # 如果有2个或更多共同词，认为可能是匹配的
            if len(clean_words.intersection(known_words)) >= 2:
                return code
        
        return None
    
    def add_known_mapping(self, english_name: str, ebird_code: str):
        """添加已知的映射"""
        clean_name = self.clean_name(english_name)
        self.known_mappings[clean_name] = ebird_code
    
    def generate_ebird_code_guess(self, english_name: str) -> str:
        """
        为未知的鸟类生成一个eBird代码的猜测
        这不是真实的代码，仅用于演示
        """
        if not english_name:
            return ""
        
        clean_name = self.clean_name(english_name)
        words = clean_name.lower().split()
        
        if not words:
            return ""
        
        # 生成代码：取每个词的前几个字母
        code_parts = []
        for word in words[:3]:  # 最多3个词
            if len(word) >= 3:
                code_parts.append(word[:3])
            else:
                code_parts.append(word)
        
        # 组合并添加数字
        base_code = ''.join(code_parts)[:6]  # 限制长度
        return base_code + '1'  # 添加版本号
    
    def get_mapping_stats(self) -> Dict[str, int]:
        """获取映射统计信息"""
        return {
            'total_known_mappings': len(self.known_mappings),
            'australian_birds': len([k for k in self.known_mappings.keys() if 'australian' in k.lower()]),
            'chinese_birds': len([k for k in self.known_mappings.keys() if any(word in k.lower() for word in ['chinese', 'oriental'])]),
            'common_birds': len([k for k in self.known_mappings.keys() if 'common' in k.lower()])
        }


# 测试映射器
if __name__ == "__main__":
    mapper = EnglishToEbirdMapper()
    
    # 测试一些名称
    test_names = [
        "Australian Magpie",
        "Laughing Kookaburra", 
        "House Sparrow",
        "Unknown Bird Species",
        "Red-billed Blue Magpie"
    ]
    
    print("=== 英文名到eBird代码映射测试 ===")
    for name in test_names:
        code = mapper.name_to_ebird_code(name)
        guess = mapper.generate_ebird_code_guess(name)
        print(f"名称: {name}")
        print(f"  已知代码: {code}")
        print(f"  猜测代码: {guess}")
        print()
    
    print("映射统计:", mapper.get_mapping_stats())