#!/usr/bin/env python3
"""
智能补丁生成器
根据错误日志和需求自动生成补丁代码
"""
import json
import ast
import inspect
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import openai
from datetime import datetime
import logging
import re

logger = logging.getLogger(__name__)

class PatchGenerator:
    """智能补丁生成器"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.template_dir = Path("dna_patches/templates")
        self.template_dir.mkdir(exist_ok=True, parents=True)
        
    def generate_from_error_log(self, 
                               error_log: Dict[str, Any], 
                               target_code: str) -> Dict[str, Any]:
        """根据错误日志生成补丁"""
        try:
            # 提取错误信息
            error_message = error_log.get("message", "")
            error_type = error_log.get("error_type", "unknown")
            target_module = error_log.get("module", "unknown")
            
            # 分析错误模式
            error_pattern = self._analyze_error_pattern(error_message, target_code)
            
            # 生成补丁代码
            if error_pattern["type"] == "exception_handling":
                patch_code = self._generate_exception_handler(error_pattern, target_code)
            elif error_pattern["type"] == "performance_issue":
                patch_code = self._generate_performance_patch(error_pattern, target_code)
            elif error_pattern["type"] == "logic_error":
                patch_code = self._generate_logic_patch(error_pattern, target_code)
            else:
                patch_code = self._generate_general_patch(error_pattern, target_code)
            
            # 生成补丁元信息
            patch_info = self._generate_patch_info(error_log, error_pattern)
            
            return {
                "success": True,
                "patch_code": patch_code,
                "patch_info": patch_info,
                "error_analysis": error_pattern
            }
            
        except Exception as e:
            logger.error(f"生成补丁失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def generate_from_requirement(self,
                                 requirement: str,
                                 target_module: str,
                                 target_function: str) -> Dict[str, Any]:
        """根据需求描述生成补丁"""
        try:
            # 解析需求
            req_analysis = self._analyze_requirement(requirement)
            
            # 生成补丁代码
            if req_analysis["category"] == "new_feature":
                patch_code = self._generate_feature_patch(req_analysis, target_module, target_function)
            elif req_analysis["category"] == "optimization":
                patch_code = self._generate_optimization_patch(req_analysis, target_module, target_function)
            elif req_analysis["category"] == "bug_fix":
                patch_code = self._generate_bugfix_patch(req_analysis, target_module, target_function)
            else:
                patch_code = self._generate_custom_patch(req_analysis, target_module, target_function)
            
            # 生成补丁元信息
            patch_info = {
                "name": f"{req_analysis['category']}_{target_module}_{target_function}",
                "version": "1.0.0",
                "description": requirement,
                "author": "ai_patch_generator",
                "created_at": datetime.now().isoformat(),
                "target_module": target_module,
                "target_function": target_function,
                "priority": req_analysis.get("priority", 3),
                "dependencies": [],
                "compatibility": ["OPEN_SOURCE_MUSEUM_AI_V1.2"],
                "rollback_supported": True
            }
            
            return {
                "success": True,
                "patch_code": patch_code,
                "patch_info": patch_info,
                "requirement_analysis": req_analysis
            }
            
        except Exception as e:
            logger.error(f"根据需求生成补丁失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def _analyze_error_pattern(self, error_message: str, target_code: str) -> Dict[str, Any]:
        """分析错误模式"""
        # 常见错误模式识别
        patterns = [
            {
                "name": "内存错误",
                "patterns": [r"内存", r"Memory", r"OOM", r"out of memory"],
                "type": "performance_issue",
                "severity": "critical"
            },
            {
                "name": "连接错误",
                "patterns": [r"连接", r"Connection", r"网络", r"Network"],
                "type": "exception_handling",
                "severity": "high"
            },
            {
                "name": "超时错误",
                "patterns": [r"超时", r"Timeout", r"时间.*?长"],
                "type": "performance_issue",
                "severity": "medium"
            },
            {
                "name": "空值错误",
                "patterns": [r"None", r"null", r"空值", r"为空"],
                "type": "logic_error",
                "severity": "medium"
            },
            {
                "name": "类型错误",
                "patterns": [r"类型", r"TypeError", r"AttributeError"],
                "type": "logic_error",
                "severity": "medium"
            }
        ]
        
        # 匹配错误模式
        for pattern in patterns:
            for regex in pattern["patterns"]:
                if re.search(regex, error_message, re.IGNORECASE):
                    return {
                        "type": pattern["type"],
                        "name": pattern["name"],
                        "severity": pattern["severity"],
                        "matched_pattern": regex
                    }
        
        # 默认返回通用错误
        return {
            "type": "exception_handling",
            "name": "通用错误",
            "severity": "low",
            "matched_pattern": None
        }
    
    def _analyze_requirement(self, requirement: str) -> Dict[str, Any]:
        """分析需求描述"""
        # 关键词分类
        categories = {
            "new_feature": ["增加", "添加", "新功能", "支持", "实现"],
            "optimization": ["优化", "提升", "加速", "减少", "改进"],
            "bug_fix": ["修复", "解决", "问题", "错误", "bug"],
            "security": ["安全", "防护", "加密", "验证", "权限"]
        }
        
        # 确定分类
        detected_category = "custom"
        detected_priority = 3
        
        for category, keywords in categories.items():
            for keyword in keywords:
                if keyword in requirement:
                    detected_category = category
                    
                    # 设置优先级
                    if category in ["security", "bug_fix"]:
                        detected_priority = 5
                    elif category == "optimization":
                        detected_priority = 3
                    else:
                        detected_priority = 2
                    
                    break
            if detected_category != "custom":
                break
        
        return {
            "category": detected_category,
            "priority": detected_priority,
            "original_requirement": requirement,
            "keywords": self._extract_keywords(requirement)
        }
    
    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        # 简单的关键词提取
        words = re.findall(r'[\u4e00-\u9fff]+|\w+', text)
        
        # 过滤停用词
        stop_words = {"的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好", "自己", "这"}
        
        keywords = []
        for word in words:
            if len(word) > 1 and word not in stop_words:
                keywords.append(word)
        
        return keywords[:10]  # 最多返回10个关键词
    
    def _generate_exception_handler(self, 
                                   error_pattern: Dict[str, Any], 
                                   target_code: str) -> str:
        """生成异常处理补丁"""
        template = '''
import functools
import logging
import asyncio
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

def patch_{module}_{function}(original_func):
    """
    异常处理补丁: 增强{module}.{function}的异常处理能力
    错误类型: {error_name}
    严重程度: {severity}
    """
    
    @functools.wraps(original_func)
    async def wrapped_func(*args, **kwargs):
        try:
            # 调用原始函数
            result = await original_func(*args, **kwargs)
            return result
            
        except Exception as e:
            # 记录详细错误信息
            logger.error(
                "补丁捕获到异常: {error_name}",
                extra={{
                    "dna_module": "{module}",
                    "function": "{function}",
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "args_count": len(args),
                    "kwargs_keys": list(kwargs.keys())
                }},
                exc_info=True
            )
            
            # 根据错误类型进行特定处理
            error_msg = str(e).lower()
            
            {specific_handling}
            
            # 重新抛出原始异常
            raise
    
    return wrapped_func
'''
        
        # 生成特定错误处理逻辑
        specific_handling = ""
        if error_pattern["name"] == "连接错误":
            specific_handling = '''
            # 连接错误处理：尝试重试
            if "连接" in error_msg or "connection" in error_msg:
                logger.warning("检测到连接错误，尝试重试...")
                for i in range(3):  # 最多重试3次
                    try:
                        await asyncio.sleep(1 * (i + 1))  # 指数退避
                        result = await original_func(*args, **kwargs)
                        logger.info(f"重试成功: 第{i+1}次尝试")
                        return result
                    except Exception as retry_e:
                        logger.warning(f"重试失败 {i+1}: {retry_e}")
                
                logger.error("所有重试均失败")
            '''
        
        elif error_pattern["name"] == "空值错误":
            specific_handling = '''
            # 空值错误处理：返回安全默认值
            if "none" in error_msg or "空" in error_msg or "null" in error_msg:
                logger.warning("检测到空值错误，返回安全默认值")
                
                # 尝试推断返回类型
                import inspect
                return_annotation = inspect.signature(original_func).return_annotation
                
                if return_annotation == str:
                    return ""
                elif return_annotation == list:
                    return []
                elif return_annotation == dict:
                    return {{}}
                elif return_annotation == int or return_annotation == float:
                    return 0
                else:
                    return None
            '''
        
        # 从目标代码提取模块和函数名
        module_match = re.search(r'def\s+(\w+)', target_code)
        function_name = module_match.group(1) if module_match else "unknown"
        
        # 模块名从错误模式中获取或使用默认
        module_name = error_pattern.get("module", "unknown")
        
        code = template.format(
            module=module_name,
            function=function_name,
            error_name=error_pattern["name"],
            severity=error_pattern["severity"],
            specific_handling=specific_handling
        )
        
        return code
    
    def _generate_performance_patch(self, 
                                   error_pattern: Dict[str, Any], 
                                   target_code: str) -> str:
        """生成性能优化补丁"""
        template = '''
import functools
import logging
import time
import asyncio
from typing import Any, Dict, Optional, List
from functools import lru_cache

logger = logging.getLogger(__name__)

def patch_{module}_{function}(original_func):
    """
    性能优化补丁: 优化{module}.{function}的性能
    问题类型: {error_name}
    """
    
    # 缓存机制
    cache = {{}}
    MAX_CACHE_SIZE = 100
    
    @functools.wraps(original_func)
    async def wrapped_func(*args, **kwargs):
        start_time = time.time()
        
        try:
            {optimization_logic}
            
            # 调用原始函数
            result = await original_func(*args, **kwargs)
            
            end_time = time.time()
            execution_time = (end_time - start_time) * 1000  # 转换为毫秒
            
            # 记录性能指标
            if execution_time > 1000:  # 超过1秒
                logger.warning(
                    "函数执行时间较长",
                    extra={{
                        "dna_module": "{module}",
                        "function": "{function}",
                        "execution_time_ms": round(execution_time, 2),
                        "cache_hit": getattr(wrapped_func, '_cache_hit', False)
                    }}
                )
            
            return result
            
        except Exception as e:
            end_time = time.time()
            logger.error(
                "性能补丁执行失败",
                extra={{
                    "dna_module": "{module}",
                    "function": "{function}",
                    "execution_time_ms": round((end_time - start_time) * 1000, 2),
                    "error": str(e)
                }}
            )
            raise
    
    return wrapped_func
'''
        
        # 根据错误类型生成优化逻辑
        optimization_logic = ""
        if error_pattern["name"] == "内存错误":
            optimization_logic = '''
            # 内存优化：限制缓存大小
            import hashlib
            import pickle
            
            # 生成缓存键
            cache_key_data = pickle.dumps((args, tuple(sorted(kwargs.items()))))
            cache_key = hashlib.md5(cache_key_data).hexdigest()
            
            # 检查缓存
            if cache_key in cache:
                wrapped_func._cache_hit = True
                logger.debug(f"缓存命中: {cache_key[:8]}")
                return cache[cache_key]
            
            wrapped_func._cache_hit = False
            
            # 清理过期缓存
            if len(cache) >= MAX_CACHE_SIZE:
                # 移除最旧的缓存项
                oldest_key = next(iter(cache))
                del cache[oldest_key]
                logger.debug(f"清理缓存: {oldest_key[:8]}")
            '''
        
        elif error_pattern["name"] == "超时错误":
            optimization_logic = '''
            # 超时优化：设置执行超时
            timeout_seconds = 30  # 默认30秒超时
            
            try:
                # 使用asyncio.wait_for设置超时
                result = await asyncio.wait_for(
                    original_func(*args, **kwargs),
                    timeout=timeout_seconds
                )
                return result
                
            except asyncio.TimeoutError:
                logger.error(
                    "函数执行超时",
                    extra={{
                        "dna_module": "{module}",
                        "function": "{function}",
                        "timeout_seconds": timeout_seconds
                    }}
                )
                raise TimeoutError(f"函数执行超时: {timeout_seconds}秒")
            '''
        
        # 从目标代码提取信息
        module_match = re.search(r'class\s+(\w+)|def\s+(\w+)', target_code)
        if module_match:
            module_name = module_match.group(1) or module_match.group(2) or "unknown"
        else:
            module_name = "unknown"
        
        function_match = re.search(r'def\s+(\w+)', target_code)
        function_name = function_match.group(1) if function_match else "unknown"
        
        code = template.format(
            module=module_name,
            function=function_name,
            error_name=error_pattern["name"],
            optimization_logic=optimization_logic
        )
        
        return code
    
    def _generate_feature_patch(self, 
                               req_analysis: Dict[str, Any], 
                               target_module: str,
                               target_function: str) -> str:
        """生成新功能补丁"""
        template = '''
"""
新功能补丁: {description}
需求分类: {category}
关键词: {keywords}
"""

import functools
import logging
import asyncio
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime

logger = logging.getLogger(__name__)

def patch_{module}_{function}(original_func):
    """
    新功能增强补丁
    为 {module}.{function} 添加新功能: {description}
    """
    
    # 新功能的配置
    NEW_FEATURE_CONFIG = {{
        "enabled": True,
        "log_level": "INFO",
        "max_retries": 3,
        "timeout_seconds": 10
    }}
    
    @functools.wraps(original_func)
    async def wrapped_func(*args, **kwargs):
        start_time = datetime.now()
        
        try:
            # 1. 前置处理：记录输入参数
            if NEW_FEATURE_CONFIG["enabled"]:
                logger.log(
                    getattr(logging, NEW_FEATURE_CONFIG["log_level"]),
                    "新功能补丁 - 开始执行",
                    extra={{
                        "dna_module": "{module}",
                        "function": "{function}",
                        "args_count": len(args),
                        "kwargs_keys": list(kwargs.keys()),
                        "timestamp": start_time.isoformat()
                    }}
                )
            
            {pre_processing}
            
            # 2. 调用原始函数
            result = await original_func(*args, **kwargs)
            
            {post_processing}
            
            # 3. 后置处理：记录结果和性能
            if NEW_FEATURE_CONFIG["enabled"]:
                end_time = datetime.now()
                execution_time = (end_time - start_time).total_seconds()
                
                logger.log(
                    getattr(logging, NEW_FEATURE_CONFIG["log_level"]),
                    "新功能补丁 - 执行完成",
                    extra={{
                        "dna_module": "{module}",
                        "function": "{function}",
                        "execution_time_seconds": execution_time,
                        "timestamp": end_time.isoformat(),
                        "success": True
                    }}
                )
            
            return result
            
        except Exception as e:
            # 错误处理
            if NEW_FEATURE_CONFIG["enabled"]:
                logger.error(
                    "新功能补丁 - 执行失败",
                    extra={{
                        "dna_module": "{module}",
                        "function": "{function}",
                        "error": str(e),
                        "timestamp": datetime.now().isoformat()
                    }},
                    exc_info=True
                )
            
            # 重试逻辑
            if NEW_FEATURE_CONFIG["max_retries"] > 0:
                for retry in range(NEW_FEATURE_CONFIG["max_retries"]):
                    try:
                        await asyncio.sleep(1 * (retry + 1))
                        logger.info(f"新功能补丁 - 第{{retry + 1}}次重试")
                        result = await original_func(*args, **kwargs)
                        logger.info(f"新功能补丁 - 重试成功")
                        return result
                    except Exception as retry_e:
                        logger.warning(f"新功能补丁 - 重试{{retry + 1}}失败: {{retry_e}}")
            
            # 所有重试都失败，重新抛出异常
            raise
    
    # 为包装函数添加额外方法
    {extra_methods}
    
    return wrapped_func
'''
        
        # 根据需求分类生成不同的处理逻辑
        if req_analysis["category"] == "new_feature":
            pre_processing = '''
            # 新功能：参数验证和增强
            validated_args = []
            for arg in args:
                if arg is None:
                    logger.warning("检测到None参数，使用默认值替换")
                    validated_args.append("")  # 使用空字符串作为默认值
                else:
                    validated_args.append(arg)
            
            args = tuple(validated_args)
            
            # 添加额外参数
            if "enhanced" not in kwargs:
                kwargs["enhanced"] = True
                logger.debug("添加增强参数")
            '''
            
            post_processing = '''
            # 新功能：结果增强
            if isinstance(result, dict):
                result["_enhanced_by_patch"] = True
                result["_patch_version"] = "1.0.0"
                result["_execution_timestamp"] = datetime.now().isoformat()
            elif isinstance(result, list):
                result = [{
                    "data": item,
                    "enhanced": True
                } for item in result]
            '''
            
            extra_methods = '''
    def get_feature_info():
        """获取新功能信息"""
        return {
            "name": "新功能补丁",
            "version": "1.0.0",
            "description": "{description}",
            "config": NEW_FEATURE_CONFIG
        }
    
    wrapped_func.get_feature_info = get_feature_info
    
    def enable_feature(enabled: bool = True):
        """启用或禁用新功能"""
        NEW_FEATURE_CONFIG["enabled"] = enabled
        logger.info(f"新功能{'启用' if enabled else '禁用'}")
    
    wrapped_func.enable_feature = enable_feature
            '''.format(description=req_analysis["original_requirement"])
        
        else:
            pre_processing = "# 默认前置处理"
            post_processing = "# 默认后置处理"
            extra_methods = "# 无额外方法"
        
        code = template.format(
            module=target_module,
            function=target_function,
            description=req_analysis["original_requirement"],
            category=req_analysis["category"],
            keywords=", ".join(req_analysis["keywords"]),
            pre_processing=pre_processing,
            post_processing=post_processing,
            extra_methods=extra_methods
        )
        
        return code
    
    def save_patch(self, 
                  patch_code: str, 
                  patch_info: Dict[str, Any]) -> str:
        """保存补丁到文件"""
        # 生成补丁ID
        patch_id = hashlib.md5(patch_code.encode()).hexdigest()[:16]
        
        # 创建完整补丁文件
        full_patch = f'''"""
{patch_info.get('description', '自动生成的补丁')}

PATCH_INFO:
  name: "{patch_info.get('name', 'unnamed_patch')}"
  version: "{patch_info.get('version', '1.0.0')}"
  description: "{patch_info.get('description', '')}"
  author: "{patch_info.get('author', 'ai_patch_generator')}"
  created_at: "{patch_info.get('created_at', datetime.now().isoformat())}"
  target_module: "{patch_info.get('target_module', 'unknown')}"
  target_function: "{patch_info.get('target_function', 'unknown')}"
  priority: {patch_info.get('priority', 3)}
  dependencies: {json.dumps(patch_info.get('dependencies', []), ensure_ascii=False)}
  compatibility: {json.dumps(patch_info.get('compatibility', ['OPEN_SOURCE_MUSEUM_AI_V1.2']), ensure_ascii=False)}
  rollback_supported: {str(patch_info.get('rollback_supported', True)).lower()}
"""

{patch_code}

if __name__ == "__main__":
    print("补丁文件生成完成")
    print(f"补丁ID: {patch_id}")
    print(f"目标: {{patch_info.get('target_module')}}.{{patch_info.get('target_function')}}")
'''
        
        # 保存文件
        patch_file = self.template_dir / f"patch_{patch_id}.py"
        with open(patch_file, 'w', encoding='utf-8') as f:
            f.write(full_patch)
        
        logger.info(f"补丁已保存: {patch_file}")
        
        return str(patch_file)

def main():
    """命令行界面"""
    import argparse
    
    parser = argparse.ArgumentParser(description="智能补丁生成器")
    parser.add_argument("--from-error", type=str, help="从错误日志生成补丁")
    parser.add_argument("--from-requirement", type=str, help="从需求描述生成补丁")
    parser.add_argument("--target-module", type=str, help="目标模块名")
    parser.add_argument("--target-function", type=str, help="目标函数名")
    parser.add_argument("--target-code", type=str, help="目标代码文件")
    parser.add_argument("--output", type=str, help="输出文件")
    
    args = parser.parse_args()
    
    generator = PatchGenerator()
    
    if args.from_error and args.target_code:
        # 从错误日志生成
        with open(args.from_error, 'r', encoding='utf-8') as f:
            error_log = json.load(f)
        
        with open(args.target_code, 'r', encoding='utf-8') as f:
            target_code = f.read()
        
        result = generator.generate_from_error_log(error_log, target_code)
        
        if result['success']:
            print("✅ 补丁生成成功！")
            print(f"错误分析: {result['error_analysis']}")
            
            # 保存补丁
            if args.output:
                patch_file = generator.save_patch(
                    result['patch_code'],
                    result['patch_info']
                )
                print(f"📁 补丁已保存: {patch_file}")
            else:
                print("\n生成的补丁代码:")
                print("-" * 60)
                print(result['patch_code'][:1000] + "..." if len(result['patch_code']) > 1000 else result['patch_code'])
        else:
            print(f"❌ 补丁生成失败: {result['error']}")
    
    elif args.from_requirement and args.target_module and args.target_function:
        # 从需求生成
        result = generator.generate_from_requirement(
            args.from_requirement,
            args.target_module,
            args.target_function
        )
        
        if result['success']:
            print("✅ 补丁生成成功！")
            print(f"需求分析: {result['requirement_analysis']}")
            
            # 保存补丁
            if args.output:
                patch_file = generator.save_patch(
                    result['patch_code'],
                    result['patch_info']
                )
                print(f"📁 补丁已保存: {patch_file}")
            else:
                print("\n生成的补丁代码:")
                print("-" * 60)
                print(result['patch_code'][:1000] + "..." if len(result['patch_code']) > 1000 else result['patch_code'])
        else:
            print(f"❌ 补丁生成失败: {result['error']}")
    
    else:
        parser.print_help()
        print("\n示例:")
        print("  从错误日志生成: --from-error error.json --target-code module.py")
        print("  从需求生成: --from-requirement '优化性能' --target-module brain --target-function process")

if __name__ == "__main__":
    main()
