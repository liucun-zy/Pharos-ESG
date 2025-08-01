"""
结构增强模块处理管道

提供：
- StructureEnhancementPipeline: 单文件处理管道
- BatchStructureEnhancementPipeline: 批量处理管道
- AblationExperimentRunner: 消融实验运行器
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from .config import StructureEnhancementConfig
from .processors import TitleExtractor, PageGrouper, TitleAligner, StructureEnhancer
from .utils import setup_logging, timing_context, ProcessingStats, ensure_directory


class StructureEnhancementPipeline:
    """结构增强单文件处理管道"""
    
    def __init__(self, config: StructureEnhancementConfig):
        self.config = config
        self.logger = setup_logging(
            config.log_level,
            config.log_file_path if config.log_to_file else None,
            "structure_enhancement.Pipeline"
        )
        
        # 初始化处理器
        self.title_extractor = TitleExtractor(config)
        self.page_grouper = PageGrouper(config)
        self.title_aligner = TitleAligner(config)
        self.structure_enhancer = StructureEnhancer(config)
        
        self.stats = ProcessingStats()
    
    def run(self, input_md_path: str, titles_json_path: Optional[str] = None, 
            output_dir: Optional[str] = None, toc_image_path: Optional[str] = None) -> Dict[str, Any]:
        """
        运行完整的结构增强流程
        
        Args:
            input_md_path: 输入Markdown文件路径
            titles_json_path: 标题JSON文件路径（可选，如果不提供将尝试从图片提取）
            output_dir: 输出目录路径
            toc_image_path: 目录页面图片路径（用于标题提取）
        
        Returns:
            处理结果字典
        """
        self.stats.reset()
        
        with timing_context(self.logger, f"结构增强流程 - {self.config.experiment_name}"):
            try:
                # 确保输出目录存在
                if output_dir:
                    ensure_directory(output_dir)
                
                results = {}
                
                # 步骤1: 标题提取（如果需要）
                if not titles_json_path and toc_image_path:
                    self.logger.info("开始标题提取阶段")
                    titles_json_path = os.path.join(output_dir, "extracted_titles.json") if output_dir else "extracted_titles.json"
                    
                    extraction_result = self.title_extractor.process(
                        image_path=toc_image_path,
                        output_json_path=titles_json_path
                    )
                    results["title_extraction"] = extraction_result
                    
                    if not extraction_result["success"]:
                        raise Exception(f"标题提取失败: {extraction_result.get('error', 'Unknown error')}")
                
                # 步骤2: 页面分组
                self.logger.info("开始页面分组阶段")
                grouped_md_path = os.path.join(output_dir, "grouped.md") if output_dir else None
                
                grouping_result = self.page_grouper.process(
                    input_md_path=input_md_path,
                    output_md_path=grouped_md_path
                )
                results["page_grouping"] = grouping_result
                
                if not grouping_result["success"]:
                    raise Exception(f"页面分组失败: {grouping_result.get('error', 'Unknown error')}")
                
                # 步骤3: 标题对齐（如果有标题JSON）
                if titles_json_path and Path(titles_json_path).exists():
                    self.logger.info("开始标题对齐阶段")
                    aligned_md_path = os.path.join(output_dir, "aligned.md") if output_dir else None
                    
                    alignment_result = self.title_aligner.process(
                        md_content=grouping_result["output_content"],
                        titles_json_path=titles_json_path,
                        output_md_path=aligned_md_path
                    )
                    results["title_alignment"] = alignment_result
                    
                    if not alignment_result["success"]:
                        self.logger.warning(f"标题对齐失败: {alignment_result.get('error', 'Unknown error')}")
                        # 标题对齐失败不是致命错误，继续处理
                
                # 生成处理报告
                report = self._generate_processing_report(results)
                
                # 保存处理报告
                if output_dir:
                    report_path = os.path.join(output_dir, "processing_report.json")
                    with open(report_path, 'w', encoding='utf-8') as f:
                        json.dump(report, f, indent=2, ensure_ascii=False)
                
                self.stats.add_success()
                self.stats.finish()
                
                return {
                    "success": True,
                    "experiment_name": self.config.experiment_name,
                    "results": results,
                    "report": report,
                    "output_dir": output_dir,
                    "stats": self.stats.to_dict()
                }
                
            except Exception as e:
                self.logger.error(f"处理流程失败: {e}")
                self.stats.add_failure(str(e))
                self.stats.finish()
                
                return {
                    "success": False,
                    "experiment_name": self.config.experiment_name,
                    "error": str(e),
                    "stats": self.stats.to_dict()
                }
    
    def _generate_processing_report(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """生成处理报告"""
        report = {
            "experiment_name": self.config.experiment_name,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "config_summary": {
                "title_similarity_threshold": self.config.title_similarity_threshold,
                "fuzzy_match_enabled": self.config.fuzzy_match_enabled,
                "use_llm_matching": self.config.use_llm_matching,
                "auto_insert_missing_titles": self.config.auto_insert_missing_titles,
                "max_title_levels": self.config.max_title_levels
            },
            "stages": {}
        }
        
        # 汇总各阶段结果
        for stage_name, stage_result in results.items():
            if isinstance(stage_result, dict) and "stats" in stage_result:
                report["stages"][stage_name] = {
                    "success": stage_result.get("success", False),
                    "duration": stage_result["stats"].get("duration", 0),
                    "operations": stage_result["stats"].get("total_operations", 0),
                    "success_rate": stage_result["stats"].get("success_rate", 0)
                }
                
                if not stage_result.get("success", False):
                    report["stages"][stage_name]["error"] = stage_result.get("error", "Unknown error")
        
        # 计算总体统计
        total_duration = sum(stage.get("duration", 0) for stage in report["stages"].values())
        total_operations = sum(stage.get("operations", 0) for stage in report["stages"].values())
        successful_stages = sum(1 for stage in report["stages"].values() if stage.get("success", False))
        
        report["summary"] = {
            "total_duration": total_duration,
            "total_operations": total_operations,
            "successful_stages": successful_stages,
            "total_stages": len(report["stages"]),
            "overall_success_rate": successful_stages / max(1, len(report["stages"]))
        }
        
        return report


class BatchStructureEnhancementPipeline:
    """批量结构增强处理管道"""
    
    def __init__(self, config: StructureEnhancementConfig):
        self.config = config
        self.logger = setup_logging(
            config.log_level,
            config.log_file_path if config.log_to_file else None,
            "structure_enhancement.BatchPipeline"
        )
        self.stats = ProcessingStats()
    
    def run_batch(self, input_files: List[str], output_base_dir: str, 
                  max_workers: int = 4, **kwargs) -> Dict[str, Any]:
        """
        批量处理多个文件
        
        Args:
            input_files: 输入文件路径列表
            output_base_dir: 输出基础目录
            max_workers: 最大并发工作线程数
            **kwargs: 传递给单文件处理的额外参数
        
        Returns:
            批量处理结果字典
        """
        self.stats.reset()
        
        with timing_context(self.logger, f"批量处理 - {len(input_files)}个文件"):
            try:
                ensure_directory(output_base_dir)
                
                results = {}
                failed_files = []
                
                # 并发处理文件
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    # 提交任务
                    future_to_file = {}
                    for input_file in input_files:
                        file_name = Path(input_file).stem
                        output_dir = os.path.join(output_base_dir, file_name)
                        
                        future = executor.submit(
                            self._process_single_file,
                            input_file,
                            output_dir,
                            **kwargs
                        )
                        future_to_file[future] = input_file
                    
                    # 收集结果
                    for future in as_completed(future_to_file):
                        input_file = future_to_file[future]
                        try:
                            result = future.result()
                            results[input_file] = result
                            
                            if result["success"]:
                                self.stats.add_success()
                                self.logger.info(f"成功处理: {input_file}")
                            else:
                                self.stats.add_failure(result.get("error", "Unknown error"))
                                failed_files.append(input_file)
                                self.logger.error(f"处理失败: {input_file}")
                            
                            self.stats.increment_files()
                            
                        except Exception as e:
                            error_msg = f"处理异常 {input_file}: {e}"
                            self.logger.error(error_msg)
                            self.stats.add_failure(error_msg)
                            failed_files.append(input_file)
                            results[input_file] = {
                                "success": False,
                                "error": str(e)
                            }
                
                # 生成批量处理报告
                batch_report = self._generate_batch_report(results, input_files, failed_files)
                
                # 保存批量报告
                report_path = os.path.join(output_base_dir, "batch_processing_report.json")
                with open(report_path, 'w', encoding='utf-8') as f:
                    json.dump(batch_report, f, indent=2, ensure_ascii=False)
                
                self.stats.finish()
                
                return {
                    "success": len(failed_files) == 0,
                    "results": results,
                    "batch_report": batch_report,
                    "failed_files": failed_files,
                    "stats": self.stats.to_dict()
                }
                
            except Exception as e:
                self.logger.error(f"批量处理失败: {e}")
                self.stats.add_failure(str(e))
                self.stats.finish()
                
                return {
                    "success": False,
                    "error": str(e),
                    "stats": self.stats.to_dict()
                }
    
    def _process_single_file(self, input_file: str, output_dir: str, **kwargs) -> Dict[str, Any]:
        """处理单个文件"""
        pipeline = StructureEnhancementPipeline(self.config)
        return pipeline.run(input_file, output_dir=output_dir, **kwargs)
    
    def _generate_batch_report(self, results: Dict[str, Any], input_files: List[str], 
                              failed_files: List[str]) -> Dict[str, Any]:
        """生成批量处理报告"""
        successful_files = [f for f in input_files if f not in failed_files]
        
        # 计算平均统计
        total_duration = 0
        total_operations = 0
        stage_success_rates = {}
        
        for file_path, result in results.items():
            if result.get("success") and "report" in result:
                report = result["report"]
                total_duration += report["summary"].get("total_duration", 0)
                total_operations += report["summary"].get("total_operations", 0)
                
                # 收集各阶段成功率
                for stage_name, stage_info in report["stages"].items():
                    if stage_name not in stage_success_rates:
                        stage_success_rates[stage_name] = []
                    stage_success_rates[stage_name].append(stage_info.get("success_rate", 0))
        
        # 计算平均成功率
        avg_stage_success_rates = {}
        for stage_name, rates in stage_success_rates.items():
            avg_stage_success_rates[stage_name] = sum(rates) / len(rates) if rates else 0
        
        return {
            "experiment_name": self.config.experiment_name,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "summary": {
                "total_files": len(input_files),
                "successful_files": len(successful_files),
                "failed_files": len(failed_files),
                "success_rate": len(successful_files) / len(input_files) if input_files else 0,
                "total_duration": total_duration,
                "avg_duration_per_file": total_duration / len(successful_files) if successful_files else 0,
                "total_operations": total_operations
            },
            "stage_performance": avg_stage_success_rates,
            "failed_files": failed_files,
            "config_summary": {
                "title_similarity_threshold": self.config.title_similarity_threshold,
                "fuzzy_match_enabled": self.config.fuzzy_match_enabled,
                "use_llm_matching": self.config.use_llm_matching,
                "auto_insert_missing_titles": self.config.auto_insert_missing_titles
            }
        }


class AblationExperimentRunner:
    """消融实验运行器"""
    
    def __init__(self, base_config: StructureEnhancementConfig, experiments: List[str]):
        self.base_config = base_config
        self.experiments = experiments
        self.logger = setup_logging(
            base_config.log_level,
            base_config.log_file_path if base_config.log_to_file else None,
            "structure_enhancement.AblationRunner"
        )
    
    def run_experiments(self, input_files: List[str], output_base_dir: str, 
                       **kwargs) -> Dict[str, Dict[str, Any]]:
        """
        运行消融实验
        
        Args:
            input_files: 输入文件列表
            output_base_dir: 输出基础目录
            **kwargs: 传递给处理管道的额外参数
        
        Returns:
            实验结果字典
        """
        ensure_directory(output_base_dir)
        
        experiment_results = {}
        
        # 运行基线实验
        self.logger.info("运行基线实验...")
        baseline_config = self.base_config.copy()
        baseline_config.experiment_name = "baseline"
        
        baseline_output_dir = os.path.join(output_base_dir, "baseline")
        baseline_pipeline = BatchStructureEnhancementPipeline(baseline_config)
        baseline_result = baseline_pipeline.run_batch(input_files, baseline_output_dir, **kwargs)
        experiment_results["baseline"] = baseline_result
        
        # 运行消融实验
        for experiment_name in self.experiments:
            self.logger.info(f"运行消融实验: {experiment_name}")
            
            # 创建实验配置
            experiment_config = self.base_config.copy()
            experiment_config.apply_ablation(experiment_name)
            
            # 运行实验
            experiment_output_dir = os.path.join(output_base_dir, experiment_name)
            experiment_pipeline = BatchStructureEnhancementPipeline(experiment_config)
            experiment_result = experiment_pipeline.run_batch(input_files, experiment_output_dir, **kwargs)
            experiment_results[experiment_name] = experiment_result
        
        # 生成对比报告
        comparison_report = self._generate_comparison_report(experiment_results)
        
        # 保存对比报告
        report_path = os.path.join(output_base_dir, "ablation_comparison_report.json")
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(comparison_report, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"消融实验完成，结果保存至: {output_base_dir}")
        
        return experiment_results
    
    def _generate_comparison_report(self, experiment_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """生成对比报告"""
        comparison = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "experiments": {},
            "performance_comparison": {},
            "ranking": []
        }
        
        # 提取各实验的关键指标
        for exp_name, result in experiment_results.items():
            if result.get("success") and "batch_report" in result:
                batch_report = result["batch_report"]
                summary = batch_report["summary"]
                
                comparison["experiments"][exp_name] = {
                    "success_rate": summary.get("success_rate", 0),
                    "avg_duration": summary.get("avg_duration_per_file", 0),
                    "total_operations": summary.get("total_operations", 0),
                    "stage_performance": batch_report.get("stage_performance", {})
                }
        
        # 性能对比
        if "baseline" in comparison["experiments"]:
            baseline_metrics = comparison["experiments"]["baseline"]
            
            for exp_name, metrics in comparison["experiments"].items():
                if exp_name != "baseline":
                    comparison["performance_comparison"][exp_name] = {
                        "success_rate_change": metrics["success_rate"] - baseline_metrics["success_rate"],
                        "duration_change": metrics["avg_duration"] - baseline_metrics["avg_duration"],
                        "operations_change": metrics["total_operations"] - baseline_metrics["total_operations"]
                    }
        
        # 排名（按成功率排序）
        ranking = sorted(
            comparison["experiments"].items(),
            key=lambda x: x[1]["success_rate"],
            reverse=True
        )
        comparison["ranking"] = [{"experiment": name, "success_rate": metrics["success_rate"]} 
                               for name, metrics in ranking]
        
        return comparison 