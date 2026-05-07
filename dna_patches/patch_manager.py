#!/usr/bin/env python3
"""
DNA补丁管理器
功能: 动态加载和管理系统补丁
"""
import importlib
import inspect
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, Type, Union
from datetime import datetime
import asyncio
import logging
from dataclasses import dataclass, asdict
import yaml

logger = logging.getLogger(__name__)

@dataclass
class PatchInfo:
    """补丁信息"""
    patch_id: str
    name: str
    version: str
    description: str
    author: str
    created_at: str
    target_module: str
    target_function: str
    priority: int = 0
    dependencies: List[str] = None
    compatibility: List[str] = None
    applied: bool = False
    applied_at: Optional[str] = None
    rollback_supported: bool = True
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.compatibility is None:
            self.compatibility = ["OPEN_SOURCE_MUSEUM_AI_V1.2"]

class PatchManager:
    """补丁管理器"""
    
    def __init__(self, patches_dir: str = "dna_patches/patches"):
        self.patches_dir = Path(patches_dir)
        self.patches_dir.mkdir(exist_ok=True, parents=True)
        
        self.patches: Dict[str, PatchInfo] = {}
        self.applied_patches: Dict[str, PatchInfo] = {}
        self.original_functions: Dict[str, Callable] = {}
        
        self.patch_log_file = Path("dna_logs/patch_log.json")
        self.patch_log_file.parent.mkdir(exist_ok=True)
        
        self.load_patches()
    
    def load_patches(self):
        """加载所有补丁"""
        patch_files = list(self.patches_dir.glob("*.py"))
        
        for patch_file in patch_files:
            try:
                # 解析补丁信息
                patch_info = self._parse_patch_info(patch_file)
                if patch_info:
                    self.patches[patch_info.patch_id] = patch_info
                    logger.info(f"加载补丁: {patch_info.name} v{patch_info.version}")
            except Exception as e:
                logger.error(f"加载补丁失败 {patch_file}: {e}")
        
        # 加载应用记录
        self._load_application_log()
    
    def _parse_patch_info(self, patch_file: Path) -> Optional[PatchInfo]:
        """解析补丁文件，提取元信息"""
        with open(patch_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 查找补丁信息注释
        import re
        
        # 尝试从文档字符串解析
        docstring_match = re.search(r'"""(.*?)"""', content, re.DOTALL)
        if docstring_match:
            docstring = docstring_match.group(1)
            # 提取YAML格式的元信息
            yaml_match = re.search(r'PATCH_INFO:\s*\n(.*?)(?=\n\s*\n|$)', docstring, re.DOTALL)
            if yaml_match:
                try:
                    patch_data = yaml.safe_load(yaml_match.group(1))
                    patch_data['patch_id'] = hashlib.md5(content.encode()).hexdigest()[:16]
                    patch_data['created_at'] = patch_data.get('created_at', datetime.now().isoformat())
                    return PatchInfo(**patch_data)
                except Exception as e:
                    logger.warning(f"解析补丁元信息失败: {e}")
        
        # 从文件头注释解析
        header_match = re.search(r'#\s*Patch:\s*(.*?)\n#\s*Version:\s*(.*?)\n', content)
        if header_match:
            name = header_match.group(1).strip()
            version = header_match.group(2).strip()
            
            # 从函数定义推断目标
            func_match = re.search(r'def\s+patch_(\w+)_(\w+)', content)
            if func_match:
                target_module = func_match.group(1)
                target_function = func_match.group(2)
                
                return PatchInfo(
                    patch_id=hashlib.md5(content.encode()).hexdigest()[:16],
                    name=name,
                    version=version,
                    description=f"自动提取的补丁: {name}",
                    author="auto-extracted",
                    created_at=datetime.now().isoformat(),
                    target_module=target_module,
                    target_function=target_function
                )
        
        return None
    
    def _load_application_log(self):
        """加载补丁应用记录"""
        if self.patch_log_file.exists():
            try:
                with open(self.patch_log_file, 'r', encoding='utf-8') as f:
                    log_data = json.load(f)
                
                for patch_id, patch_info in log_data.get("applied_patches", {}).items():
                    if patch_id in self.patches:
                        self.patches[patch_id].applied = True
                        self.patches[patch_id].applied_at = patch_info.get("applied_at")
                        self.applied_patches[patch_id] = self.patches[patch_id]
                        
            except Exception as e:
                logger.error(f"加载补丁日志失败: {e}")
    
    def _save_application_log(self):
        """保存补丁应用记录"""
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "applied_patches": {
                pid: {
                    "name": patch.name,
                    "version": patch.version,
                    "applied_at": patch.applied_at,
                    "target": f"{patch.target_module}.{patch.target_function}"
                }
                for pid, patch in self.applied_patches.items()
            },
            "dna_version": "OPEN_SOURCE_MUSEUM_AI_V1.2"
        }
        
        with open(self.patch_log_file, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
    
    async def apply_patch(self, patch_id: str) -> Dict[str, Any]:
        """应用补丁"""
        if patch_id not in self.patches:
            return {"success": False, "error": f"补丁不存在: {patch_id}"}
        
        patch = self.patches[patch_id]
        
        # 检查是否已应用
        if patch.applied:
            return {"success": True, "message": f"补丁已应用: {patch.name}"}
        
        # 检查依赖
        for dep_id in patch.dependencies:
            if dep_id not in self.applied_patches:
                return {"success": False, "error": f"缺少依赖补丁: {dep_id}"}
        
        try:
            # 导入补丁模块
            module_name = f"dna_patches.patches.{patch.patch_id}"
            spec = importlib.util.spec_from_file_location(
                module_name, 
                self.patches_dir / f"{patch.patch_id}.py"
            )
            patch_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(patch_module)
            
            # 查找补丁函数
            patch_func_name = f"patch_{patch.target_module}_{patch.target_function}"
            if not hasattr(patch_module, patch_func_name):
                return {"success": False, "error": f"补丁函数不存在: {patch_func_name}"}
            
            patch_func = getattr(patch_module, patch_func_name)
            
            # 保存原始函数
            target_module = self._import_target_module(patch.target_module)
            if target_module is None:
                return {"success": False, "error": f"目标模块不存在: {patch.target_module}"}
            
            if not hasattr(target_module, patch.target_function):
                return {"success": False, "error": f"目标函数不存在: {patch.target_function}"}
            
            original_func = getattr(target_module, patch.target_function)
            self.original_functions[f"{patch.target_module}.{patch.target_function}"] = original_func
            
            # 应用补丁
            setattr(target_module, patch.target_function, patch_func)
            
            # 更新状态
            patch.applied = True
            patch.applied_at = datetime.now().isoformat()
            self.applied_patches[patch_id] = patch
            
            # 保存记录
            self._save_application_log()
            
            logger.info(f"✅ 已应用补丁: {patch.name} v{patch.version}")
            
            return {
                "success": True,
                "message": f"补丁应用成功: {patch.name}",
                "patch_id": patch_id,
                "target": f"{patch.target_module}.{patch.target_function}",
                "applied_at": patch.applied_at
            }
            
        except Exception as e:
            logger.error(f"应用补丁失败 {patch_id}: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    async def rollback_patch(self, patch_id: str) -> Dict[str, Any]:
        """回滚补丁"""
        if patch_id not in self.applied_patches:
            return {"success": False, "error": f"补丁未应用: {patch_id}"}
        
        patch = self.applied_patches[patch_id]
        
        if not patch.rollback_supported:
            return {"success": False, "error": "此补丁不支持回滚"}
        
        try:
            # 恢复原始函数
            target_key = f"{patch.target_module}.{patch.target_function}"
            if target_key in self.original_functions:
                target_module = self._import_target_module(patch.target_module)
                if target_module:
                    setattr(target_module, patch.target_function, self.original_functions[target_key])
                    
                    # 更新状态
                    patch.applied = False
                    patch.applied_at = None
                    del self.applied_patches[patch_id]
                    del self.original_functions[target_key]
                    
                    # 保存记录
                    self._save_application_log()
                    
                    logger.info(f"↩️ 已回滚补丁: {patch.name} v{patch.version}")
                    
                    return {
                        "success": True,
                        "message": f"补丁回滚成功: {patch.name}",
                        "patch_id": patch_id
                    }
            
            return {"success": False, "error": "找不到原始函数"}
            
        except Exception as e:
            logger.error(f"回滚补丁失败 {patch_id}: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    def _import_target_module(self, module_path: str) -> Optional[Any]:
        """导入目标模块"""
        try:
            # 支持多级导入
            parts = module_path.split('.')
            
            if len(parts) == 1:
                # 顶级模块
                return importlib.import_module(parts[0])
            else:
                # 子模块
                module = importlib.import_module('.'.join(parts[:-1]))
                return module
        except ImportError as e:
            logger.error(f"导入模块失败 {module_path}: {e}")
            return None
    
    async def list_patches(self, status: str = "all") -> List[Dict[str, Any]]:
        """列出补丁"""
        patches_list = []
        
        for patch in self.patches.values():
            if status == "all" or \
               (status == "applied" and patch.applied) or \
               (status == "available" and not patch.applied):
                
                patches_list.append({
                    "id": patch.patch_id,
                    "name": patch.name,
                    "version": patch.version,
                    "description": patch.description,
                    "target": f"{patch.target_module}.{patch.target_function}",
                    "applied": patch.applied,
                    "applied_at": patch.applied_at,
                    "priority": patch.priority,
                    "dependencies": patch.dependencies
                })
        
        # 按优先级排序
        patches_list.sort(key=lambda x: (-x['priority'], x['name']))
        return patches_list
    
    async def scan_and_apply_fixes(self, log_analyzer: 'LogAnalyzer') -> Dict[str, Any]:
        """扫描日志并自动应用修复补丁"""
        report = log_analyzer.analyze_logs(hours=1)
        
        if not report.get('needs_attention'):
            return {"success": True, "message": "无需修复", "applied_patches": []}
        
        applied_patches = []
        
        # 根据错误类型查找对应补丁
        for severity in ['critical', 'high']:
            if severity in report['detailed_issues']:
                for issue in report['detailed_issues'][severity]:
                    # 查找针对此错误的补丁
                    target_patch = self._find_patch_for_issue(issue)
                    if target_patch and not target_patch.applied:
                        result = await self.apply_patch(target_patch.patch_id)
                        if result['success']:
                            applied_patches.append({
                                "patch_id": target_patch.patch_id,
                                "name": target_patch.name,
                                "issue": issue['message'][:100]
                            })
        
        return {
            "success": len(applied_patches) > 0,
            "message": f"应用了 {len(applied_patches)} 个补丁",
            "applied_patches": applied_patches,
            "total_issues": report['total_issues']
        }
    
    def _find_patch_for_issue(self, issue: Dict[str, Any]) -> Optional[PatchInfo]:
        """根据问题查找对应补丁"""
        issue_message = issue.get('message', '').lower()
        issue_module = issue.get('module', '')
        
        for patch in self.patches.values():
            # 检查模块匹配
            if patch.target_module.replace('_', '').lower() in issue_module.lower():
                # 检查补丁描述是否匹配问题
                patch_desc = patch.description.lower()
                
                # 简单的关键词匹配
                keywords = ['修复', '解决', '问题', '错误', 'bug', 'fix']
                issue_keywords = ['内存', '连接', '超时', '错误', '失败']
                
                for keyword in issue_keywords:
                    if keyword in issue_message and any(kw in patch_desc for kw in keywords):
                        return patch
        
        return None
    
    def create_patch_template(self, 
                            target_module: str, 
                            target_function: str,
                            issue_description: str) -> str:
        """创建补丁模板"""
        template = f'''"""
自动生成的补丁模板
问题: {issue_description}

PATCH_INFO:
  name: "修复_{target_module}_{target_function}"
  version: "1.0.0"
  description: "自动生成的补丁，用于修复{target_module}.{target_function}的问题"
  author: "dna_patch_generator"
  created_at: "{datetime.now().isoformat()}"
  target_module: "{target_module}"
  target_function: "{target_function}"
  priority: 5
  dependencies: []
  compatibility: ["OPEN_SOURCE_MUSEUM_AI_V1.2"]
  rollback_supported: true
"""

import functools
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

def patch_{target_module}_{target_function}(original_func):
    """
    补丁函数: 用于修复 {target_module}.{target_function}
    
    参数:
        original_func: 原始函数
        
    返回:
        包装后的函数
    """
    @functools.wraps(original_func)
    async def wrapped_func(*args, **kwargs):
        try:
            # 前置处理
            logger.info(f"补丁前置处理: {{original_func.__name__}}")
            
            # 调用原始函数
            result = await original_func(*args, **kwargs)
            
            # 后置处理
            logger.info(f"补丁后置处理: {{original_func.__name__}}")
            
            return result
            
        except Exception as e:
            # 错误处理
            logger.error(f"补丁捕获到错误: {{e}}")
            
            # 这里可以添加特定的错误处理逻辑
            # 例如: 重试、降级、返回默认值等
            
            # 重新抛出或返回降级结果
            raise
    
    return wrapped_func

# 如果需要在导入时自动应用补丁
if __name__ != "__main__":
    # 这里可以添加自动应用逻辑
    pass
'''
        
        return template

async def main():
    """补丁管理器命令行界面"""
    import argparse
    
    parser = argparse.ArgumentParser(description="DNA补丁管理器")
    parser.add_argument("--list", action="store_true", help="列出所有补丁")
    parser.add_argument("--status", choices=["all", "applied", "available"], default="all", 
                       help="过滤补丁状态")
    parser.add_argument("--apply", type=str, help="应用指定补丁")
    parser.add_argument("--rollback", type=str, help="回滚指定补丁")
    parser.add_argument("--auto-fix", action="store_true", help="自动扫描并应用修复")
    parser.add_argument("--create-template", nargs=3, 
                       help="创建补丁模板: 模块 函数 问题描述")
    
    args = parser.parse_args()
    
    manager = PatchManager()
    
    if args.list:
        patches = await manager.list_patches(args.status)
        print(f"\n🧩 DNA补丁列表 (状态: {args.status})")
        print("="*60)
        
        for patch in patches:
            status = "✅ 已应用" if patch['applied'] else "⏳ 可用"
            print(f"\n{status} | {patch['name']} v{patch['version']}")
            print(f"   目标: {patch['target']}")
            print(f"   描述: {patch['description']}")
            if patch['applied']:
                print(f"   应用时间: {patch['applied_at']}")
    
    elif args.apply:
        result = await manager.apply_patch(args.apply)
        print(f"\n应用补丁结果: {'✅ 成功' if result['success'] else '❌ 失败'}")
        if not result['success']:
            print(f"错误: {result['error']}")
        else:
            print(f"消息: {result['message']}")
    
    elif args.rollback:
        result = await manager.rollback_patch(args.rollback)
        print(f"\n回滚补丁结果: {'✅ 成功' if result['success'] else '❌ 失败'}")
        if not result['success']:
            print(f"错误: {result['error']}")
        else:
            print(f"消息: {result['message']}")
    
    elif args.auto_fix:
        from dna_logs.log_analyzer import LogAnalyzer
        analyzer = LogAnalyzer()
        result = await manager.scan_and_apply_fixes(analyzer)
        
        print(f"\n🔧 自动修复扫描结果")
        print(f"   成功: {result['success']}")
        print(f"   消息: {result['message']}")
        print(f"   发现问题: {result.get('total_issues', 0)} 个")
        
        if result.get('applied_patches'):
            print("\n   应用的补丁:")
            for patch in result['applied_patches']:
                print(f"     - {patch['name']}: {patch['issue']}")
    
    elif args.create_template:
        module, func, issue = args.create_template
        template = manager.create_patch_template(module, func, issue)
        
        # 生成补丁文件名
        patch_id = hashlib.md5(template.encode()).hexdigest()[:16]
        filename = f"dna_patches/patches/patch_{patch_id}.py"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(template)
        
        print(f"✅ 补丁模板已创建: {filename}")
        print(f"   目标: {module}.{func}")
        print(f"   问题: {issue}")
    
    else:
        parser.print_help()

if __name__ == "__main__":
    asyncio.run(main())