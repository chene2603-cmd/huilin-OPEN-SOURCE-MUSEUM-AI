#!/usr/bin/env python3
"""
DNA系统日志分析器
功能: 分析日志，自动识别问题，生成修复建议
"""
import json
import re
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import argparse
import statistics

class LogAnalyzer:
    """日志分析器"""
    
    def __init__(self, log_dir: str = "dna_logs"):
        self.log_dir = Path(log_dir)
        self.issues = []
        self.metrics = defaultdict(list)
        self.error_patterns = self._load_error_patterns()
        
    def _load_error_patterns(self) -> Dict[str, Dict[str, Any]]:
        """加载错误模式"""
        return {
            "memory_error": {
                "patterns": [
                    r"CUDA out of memory",
                    r"内存不足",
                    r"MemoryError",
                    r"内存分配失败"
                ],
                "severity": "critical",
                "suggestion": "减少批量大小或使用CPU模式"
            },
            "connection_error": {
                "patterns": [
                    r"连接失败",
                    r"Connection refused",
                    r"连接超时",
                    r"无法连接到"
                ],
                "severity": "high",
                "suggestion": "检查相关服务是否运行，网络是否正常"
            },
            "model_error": {
                "patterns": [
                    r"模型加载失败",
                    r"Model not found",
                    r"模型推理错误"
                ],
                "severity": "high",
                "suggestion": "检查模型文件是否存在，重新下载模型"
            },
            "timeout_error": {
                "patterns": [
                    r"请求超时",
                    r"Timeout",
                    r"响应时间过长"
                ],
                "severity": "medium",
                "suggestion": "优化模型参数，增加超时时间"
            },
            "data_error": {
                "patterns": [
                    r"数据格式错误",
                    r"JSON解析失败",
                    r"数据验证失败"
                ],
                "severity": "medium",
                "suggestion": "检查输入数据格式，添加数据验证"
            },
            "permission_error": {
                "patterns": [
                    r"权限被拒绝",
                    r"Permission denied",
                    r"访问被拒绝"
                ],
                "severity": "high",
                "suggestion": "检查文件和目录权限"
            }
        }
    
    def analyze_logs(self, hours: int = 24) -> Dict[str, Any]:
        """分析指定时间范围内的日志"""
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        print(f"🔍 分析日志时间范围: {start_time} 到 {end_time}")
        print(f"日志目录: {self.log_dir}")
        
        # 分析所有日志文件
        log_files = list(self.log_dir.glob("*.log"))
        if not log_files:
            print("⚠️ 未找到日志文件")
            return {}
        
        all_issues = []
        for log_file in log_files:
            print(f"分析文件: {log_file.name}")
            file_issues = self._analyze_file(log_file, start_time, end_time)
            all_issues.extend(file_issues)
        
        # 生成报告
        report = self._generate_report(all_issues)
        
        # 保存报告
        self._save_report(report)
        
        return report
    
    def _analyze_file(self, 
                     log_file: Path, 
                     start_time: datetime, 
                     end_time: datetime) -> List[Dict[str, Any]]:
        """分析单个日志文件"""
        issues = []
        
        with open(log_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    # 尝试解析为JSON
                    log_entry = json.loads(line.strip())
                    
                    # 检查时间范围
                    log_time = datetime.strptime(
                        log_entry.get("timestamp", ""), 
                        "%Y-%m-%d %H:%M:%S"
                    )
                    
                    if not (start_time <= log_time <= end_time):
                        continue
                    
                    # 检查错误和警告
                    level = log_entry.get("level", "").upper()
                    message = log_entry.get("message", "")
                    dna_module = log_entry.get("dna_module", "UNKNOWN")
                    
                    if level in ["ERROR", "WARNING", "CRITICAL"]:
                        # 分析错误类型
                        issue = self._analyze_error(
                            level, message, dna_module, 
                            log_time, log_file.name, line_num
                        )
                        if issue:
                            issues.append(issue)
                    
                    # 收集性能指标
                    if "response_time" in message:
                        self._extract_performance_metrics(message, dna_module)
                        
                except json.JSONDecodeError:
                    # 如果不是JSON格式，使用正则分析
                    self._analyze_text_line(line, log_file.name, line_num, issues)
                except Exception as e:
                    print(f"解析日志行失败: {e}")
        
        return issues
    
    def _analyze_error(self, 
                      level: str, 
                      message: str, 
                      dna_module: str,
                      timestamp: datetime,
                      filename: str,
                      line_num: int) -> Optional[Dict[str, Any]]:
        """分析错误信息"""
        issue = {
            "level": level,
            "message": message,
            "module": dna_module,
            "timestamp": timestamp.isoformat(),
            "filename": filename,
            "line": line_num,
            "error_type": "unknown",
            "severity": "low",
            "suggestion": "请查看详细日志",
            "count": 1
        }
        
        # 匹配错误模式
        for error_type, pattern_info in self.error_patterns.items():
            for pattern in pattern_info["patterns"]:
                if re.search(pattern, message, re.IGNORECASE):
                    issue["error_type"] = error_type
                    issue["severity"] = pattern_info["severity"]
                    issue["suggestion"] = pattern_info["suggestion"]
                    return issue
        
        # 如果没有匹配到已知模式，但级别是ERROR
        if level == "ERROR":
            issue["severity"] = "high"
        
        return issue
    
    def _analyze_text_line(self, 
                          line: str, 
                          filename: str, 
                          line_num: int,
                          issues: List[Dict[str, Any]]):
        """分析文本格式的日志行"""
        # 简单的文本匹配
        error_keywords = ["error", "failed", "exception", "traceback", "崩溃"]
        warning_keywords = ["warning", "warn", "deprecated", "不建议"]
        
        line_lower = line.lower()
        
        for keyword in error_keywords:
            if keyword in line_lower:
                issues.append({
                    "level": "ERROR",
                    "message": line.strip(),
                    "module": "UNKNOWN",
                    "timestamp": datetime.now().isoformat(),
                    "filename": filename,
                    "line": line_num,
                    "error_type": "text_error",
                    "severity": "medium",
                    "suggestion": "检查相关配置和代码",
                    "count": 1
                })
                break
        
        for keyword in warning_keywords:
            if keyword in line_lower:
                issues.append({
                    "level": "WARNING",
                    "message": line.strip(),
                    "module": "UNKNOWN",
                    "timestamp": datetime.now().isoformat(),
                    "filename": filename,
                    "line": line_num,
                    "error_type": "text_warning",
                    "severity": "low",
                    "suggestion": "注意相关警告信息",
                    "count": 1
                })
                break
    
    def _extract_performance_metrics(self, message: str, dna_module: str):
        """提取性能指标"""
        # 提取响应时间
        time_pattern = r"(\d+\.?\d*)\s*ms"
        matches = re.findall(time_pattern, message)
        for match in matches:
            try:
                time_ms = float(match)
                self.metrics[f"{dna_module}_response_time"].append(time_ms)
            except ValueError:
                pass
        
        # 提取内存使用
        memory_pattern = r"(\d+\.?\d*)\s*(MB|GB)"
        matches = re.findall(memory_pattern, message)
        for match in matches:
            value, unit = match
            try:
                if unit == "GB":
                    value_mb = float(value) * 1024
                else:
                    value_mb = float(value)
                self.metrics[f"{dna_module}_memory_mb"].append(value_mb)
            except ValueError:
                pass
    
    def _generate_report(self, issues: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成分析报告"""
        if not issues:
            return {"status": "healthy", "message": "未发现问题"}
        
        # 统计问题
        issue_counts = Counter([issue["error_type"] for issue in issues])
        module_counts = Counter([issue["module"] for issue in issues])
        severity_counts = Counter([issue["severity"] for issue in issues])
        
        # 按严重程度分组
        critical_issues = [i for i in issues if i["severity"] == "critical"]
        high_issues = [i for i in issues if i["severity"] == "high"]
        medium_issues = [i for i in issues if i["severity"] == "medium"]
        low_issues = [i for i in issues if i["severity"] == "low"]
        
        # 计算性能指标
        performance_summary = {}
        for metric_name, values in self.metrics.items():
            if values:
                performance_summary[metric_name] = {
                    "count": len(values),
                    "avg": statistics.mean(values),
                    "min": min(values),
                    "max": max(values),
                    "p95": statistics.quantiles(values, n=20)[18] if len(values) >= 20 else max(values)
                }
        
        # 生成建议
        suggestions = self._generate_suggestions(issues)
        
        # 整体状态评估
        if critical_issues:
            overall_status = "critical"
        elif high_issues:
            overall_status = "unhealthy"
        elif medium_issues:
            overall_status = "warning"
        elif low_issues:
            overall_status = "healthy"
        else:
            overall_status = "healthy"
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": overall_status,
            "analysis_period_hours": 24,
            "total_issues": len(issues),
            "issue_summary": {
                "by_type": dict(issue_counts),
                "by_module": dict(module_counts),
                "by_severity": dict(severity_counts)
            },
            "detailed_issues": {
                "critical": critical_issues[:10],  # 最多显示10个
                "high": high_issues[:10],
                "medium": medium_issues[:10],
                "low": low_issues[:10]
            },
            "performance_metrics": performance_summary,
            "suggestions": suggestions,
            "needs_attention": len(critical_issues) + len(high_issues) > 0
        }
        
        return report
    
    def _generate_suggestions(self, issues: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """生成修复建议"""
        suggestions = []
        seen_suggestions = set()
        
        # 按严重程度排序
        sorted_issues = sorted(issues, key=lambda x: {
            "critical": 0, "high": 1, "medium": 2, "low": 3
        }[x["severity"]])
        
        for issue in sorted_issues:
            suggestion_text = issue.get("suggestion", "")
            if suggestion_text and suggestion_text not in seen_suggestions:
                suggestions.append({
                    "severity": issue["severity"],
                    "module": issue["module"],
                    "issue_type": issue["error_type"],
                    "suggestion": suggestion_text,
                    "priority": "high" if issue["severity"] in ["critical", "high"] else "medium"
                })
                seen_suggestions.add(suggestion_text)
        
        # 添加通用建议
        generic_suggestions = [
            {
                "severity": "low",
                "module": "SYSTEM",
                "issue_type": "maintenance",
                "suggestion": "定期清理日志文件，避免磁盘空间不足",
                "priority": "low"
            },
            {
                "severity": "medium",
                "module": "SYSTEM",
                "issue_type": "monitoring",
                "suggestion": "设置监控告警，及时响应系统异常",
                "priority": "medium"
            }
        ]
        
        suggestions.extend(generic_suggestions)
        return suggestions
    
    def _save_report(self, report: Dict[str, Any]):
        """保存报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.log_dir / f"dna_analysis_report_{timestamp}.json"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        # 生成可读的文本报告
        text_report = self._generate_text_report(report)
        text_file = self.log_dir / f"dna_analysis_report_{timestamp}.txt"
        
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write(text_report)
        
        print(f"📊 分析报告已保存: {report_file}")
        print(f"📄 文本报告已保存: {text_file}")
        
        # 打印摘要
        print("\n" + "="*60)
        print("🧬 DNA系统健康分析报告")
        print("="*60)
        print(f"整体状态: {report['overall_status'].upper()}")
        print(f"发现问题: {report['total_issues']} 个")
        print(f"需要关注: {'是' if report['needs_attention'] else '否'}")
        print("="*60)
        
        if report["suggestions"]:
            print("\n💡 修复建议:")
            for i, suggestion in enumerate(report["suggestions"][:5], 1):
                print(f"{i}. [{suggestion['severity'].upper()}] {suggestion['suggestion']}")
    
    def _generate_text_report(self, report: Dict[str, Any]) -> str:
        """生成文本格式的报告"""
        lines = []
        lines.append("="*60)
        lines.append("🧬 AI文物情感交互系统DNA - 健康分析报告")
        lines.append("="*60)
        lines.append(f"生成时间: {report['timestamp']}")
        lines.append(f"分析周期: 最近{report['analysis_period_hours']}小时")
        lines.append(f"整体状态: {report['overall_status'].upper()}")
        lines.append("")
        
        lines.append("📊 问题统计:")
        lines.append(f"  总计: {report['total_issues']} 个问题")
        lines.append("")
        
        lines.append("📈 按类型统计:")
        for error_type, count in report['issue_summary']['by_type'].items():
            lines.append(f"  {error_type}: {count} 个")
        lines.append("")
        
        lines.append("🏷️ 按模块统计:")
        for module, count in report['issue_summary']['by_module'].items():
            lines.append(f"  {module}: {count} 个")
        lines.append("")
        
        lines.append("⚠️ 按严重程度统计:")
        for severity, count in report['issue_summary']['by_severity'].items():
            lines.append(f"  {severity}: {count} 个")
        lines.append("")
        
        if report.get('performance_metrics'):
            lines.append("⚡ 性能指标:")
            for metric_name, stats in report['performance_metrics'].items():
                lines.append(f"  {metric_name}:")
                lines.append(f"    平均: {stats['avg']:.2f}")
                lines.append(f"    最小: {stats['min']:.2f}")
                lines.append(f"    最大: {stats['max']:.2f}")
                if 'p95' in stats:
                    lines.append(f"    P95: {stats['p95']:.2f}")
            lines.append("")
        
        if report.get('needs_attention'):
            lines.append("🔴 需要立即关注的问题:")
            
            # 显示严重和高优先级问题
            for severity in ['critical', 'high']:
                if severity in report['detailed_issues']:
                    issues = report['detailed_issues'][severity]
                    for issue in issues[:5]:  # 最多显示5个
                        lines.append(f"  {severity.upper()}: {issue['module']} - {issue['message'][:100]}...")
            lines.append("")
        
        lines.append("💡 修复建议:")
        for i, suggestion in enumerate(report['suggestions'], 1):
            lines.append(f"{i}. [{suggestion['severity'].upper()}] {suggestion['module']}: {suggestion['suggestion']}")
        lines.append("")
        
        lines.append("🔄 下一步操作:")
        if report['needs_attention']:
            lines.append("1. 立即处理严重和高优先级问题")
            lines.append("2. 运行补丁管理器应用修复")
            lines.append("3. 重启受影响的模块")
        else:
            lines.append("1. 继续监控系统运行状态")
            lines.append("2. 考虑性能优化")
            lines.append("3. 定期进行系统维护")
        lines.append("")
        
        lines.append("="*60)
        lines.append("🧬 DNA编码: OPEN_SOURCE_MUSEUM_AI_V1.2")
        lines.append("🔧 架构师: 元宝(腾讯数字文博架构师)")
        lines.append("="*60)
        
        return "\n".join(lines)
    
    def find_repeating_errors(self, window_hours: int = 1, threshold: int = 5) -> List[Dict[str, Any]]:
        """查找重复出现的错误"""
        repeating_errors = []
        error_window = defaultdict(list)
        
        # 收集最近window_hours的错误
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=window_hours)
        
        for log_file in self.log_dir.glob("*.log"):
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        log_entry = json.loads(line.strip())
                        
                        if log_entry.get("level") != "ERROR":
                            continue
                        
                        log_time = datetime.strptime(
                            log_entry.get("timestamp", ""), 
                            "%Y-%m-%d %H:%M:%S"
                        )
                        
                        if not (start_time <= log_time <= end_time):
                            continue
                        
                        error_key = f"{log_entry.get('dna_module')}:{log_entry.get('message')[:100]}"
                        error_window[error_key].append({
                            "timestamp": log_time,
                            "module": log_entry.get("dna_module"),
                            "message": log_entry.get("message"),
                            "file": log_file.name
                        })
                        
                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue
        
        # 检查哪些错误重复出现
        for error_key, errors in error_window.items():
            if len(errors) >= threshold:
                repeating_errors.append({
                    "error_key": error_key,
                    "count": len(errors),
                    "first_occurrence": min(e["timestamp"] for e in errors).isoformat(),
                    "last_occurrence": max(e["timestamp"] for e in errors).isoformat(),
                    "module": errors[0]["module"],
                    "sample_message": errors[0]["message"][:200],
                    "files": list(set(e["file"] for e in errors))
                })
        
        return repeating_errors
    
    def generate_health_score(self) -> Dict[str, Any]:
        """生成系统健康评分"""
        # 分析最近24小时
        report = self.analyze_logs(hours=24)
        
        # 计算健康分数（0-100）
        base_score = 100
        
        # 根据问题严重程度扣分
        severity_penalties = {
            "critical": 20,
            "high": 10,
            "medium": 5,
            "low": 2
        }
        
        for severity, issues in report.get("detailed_issues", {}).items():
            penalty = severity_penalties.get(severity, 0)
            base_score -= len(issues) * penalty
        
        # 根据响应时间扣分
        for metric_name, stats in report.get("performance_metrics", {}).items():
            if "response_time" in metric_name:
                avg_time = stats.get("avg", 0)
                if avg_time > 5000:  # 5秒
                    base_score -= 10
                elif avg_time > 3000:  # 3秒
                    base_score -= 5
        
        # 确保分数在0-100之间
        health_score = max(0, min(100, base_score))
        
        # 确定等级
        if health_score >= 90:
            grade = "优秀"
        elif health_score >= 70:
            grade = "良好"
        elif health_score >= 50:
            grade = "一般"
        else:
            grade = "需要关注"
        
        return {
            "score": health_score,
            "grade": grade,
            "timestamp": datetime.now().isoformat(),
            "report_reference": report.get("timestamp"),
            "recommendations": self._get_recommendations_by_score(health_score)
        }
    
    def _get_recommendations_by_score(self, score: float) -> List[str]:
        """根据分数获取建议"""
        if score >= 90:
            return [
                "系统运行状态优秀，继续保持",
                "考虑进行性能优化以提升用户体验"
            ]
        elif score >= 70:
            return [
                "系统运行状态良好，但有改进空间",
                "关注警告级别的问题，防止升级为错误"
            ]
        elif score >= 50:
            return [
                "系统运行状态一般，需要关注",
                "立即处理高优先级问题",
                "检查系统资源配置是否充足"
            ]
        else:
            return [
                "系统运行状态不佳，需要立即处理",
                "优先处理严重和高优先级错误",
                "检查系统依赖服务是否正常",
                "考虑回滚到稳定版本"
            ]

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="AI文物情感交互系统DNA - 日志分析器")
    parser.add_argument("--hours", type=int, default=24, help="分析最近多少小时的日志")
    parser.add_argument("--output", type=str, default="console", choices=["console", "json", "both"], 
                       help="输出格式")
    parser.add_argument("--check-repeating", action="store_true", help="检查重复错误")
    parser.add_argument("--health-score", action="store_true", help="计算系统健康评分")
    parser.add_argument("--auto-fix", action="store_true", help="尝试自动修复可自动修复的问题")
    
    args = parser.parse_args()
    
    analyzer = LogAnalyzer()
    
    if args.check_repeating:
        print("🔍 检查重复出现的错误...")
        repeating_errors = analyzer.find_repeating_errors()
        
        if repeating_errors:
            print(f"发现 {len(repeating_errors)} 个重复错误:")
            for error in repeating_errors:
                print(f"\n❌ {error['module']}:")
                print(f"   次数: {error['count']}")
                print(f"   首次: {error['first_occurrence']}")
                print(f"   末次: {error['last_occurrence']}")
                print(f"   示例: {error['sample_message']}")
        else:
            print("✅ 未发现重复错误")
    
    elif args.health_score:
        print("🏥 计算系统健康评分...")
        health_info = analyzer.generate_health_score()
        
        print(f"\n健康评分: {health_info['score']}/100")
        print(f"等级: {health_info['grade']}")
        print(f"时间: {health_info['timestamp']}")
        print("\n建议:")
        for i, rec in enumerate(health_info['recommendations'], 1):
            print(f"{i}. {rec}")
    
    else:
        # 运行标准分析
        report = analyzer.analyze_logs(hours=args.hours)
        
        if args.output in ["json", "both"]:
            # 保存JSON格式报告
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            json_file = analyzer.log_dir / f"dna_analysis_{timestamp}.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            print(f"📁 JSON报告已保存: {json_file}")
        
        if args.output in ["console", "both"] and report:
            # 控制台输出摘要
            print(f"\n{'='*60}")
            print(f"🧬 DNA系统健康状态: {report['overall_status'].upper()}")
            print(f"{'='*60}")
            
            if report.get('needs_attention'):
                print("🔴 需要关注的模块:")
                for module, count in report['issue_summary']['by_module'].items():
                    if count > 0:
                        print(f"  {module}: {count} 个问题")
            
            # 显示最紧急的问题
            for severity in ['critical', 'high']:
                if severity in report['detailed_issues'] and report['detailed_issues'][severity]:
                    print(f"\n⚠️ {severity.upper()}级别问题:")
                    for issue in report['detailed_issues'][severity][:3]:
                        print(f"  - {issue['module']}: {issue['message'][:80]}...")
    
    if args.auto_fix:
        print("\n🔄 尝试自动修复...")
        # 这里可以集成自动修复逻辑
        print("自动修复功能开发中，请手动处理问题")

if __name__ == "__main__":
    main()