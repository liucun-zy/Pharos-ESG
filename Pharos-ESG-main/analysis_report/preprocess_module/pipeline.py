"""
预处理管道模块

将三个处理器组合成一个完整的预处理流程：
1. JSON转Markdown
2. 图片链接转换
3. 图片文本检测和过滤

支持：
- 灵活的处理步骤配置
- 详细的处理统计和报告
- 错误处理和恢复
- 消融实验支持
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

from .config import PreprocessConfig
from .processors import JsonToMarkdownProcessor, ImageLinkConverter, ImageTextDetector
from .utils import setup_logging, validate_paths, ensure_directory, ProcessingStats, timing_context


class PreprocessPipeline:
    """预处理管道"""
    
    def __init__(self, config: PreprocessConfig):
        self.config = config
        self.logger = setup_logging(
            log_level=config.log_level,
            log_file=config.log_file_path if config.log_to_file else None,
            logger_name="PreprocessPipeline"
        )
        
        # 初始化处理器
        self.json_processor = JsonToMarkdownProcessor(config, self.logger)
        self.image_converter = ImageLinkConverter(config, self.logger)
        self.text_detector = ImageTextDetector(config, self.logger)
        
        # 处理统计
        self.stats = ProcessingStats()
        
        self.logger.info(f"初始化预处理管道 - 实验: {config.experiment_name}")
        
    def run(self, input_json_path: str, output_dir: str) -> Dict[str, Any]:
        """
        运行完整的预处理管道
        
        Args:
            input_json_path: 输入JSON文件路径
            output_dir: 输出目录路径
        
        Returns:
            处理结果字典
        """
        with timing_context(self.logger, "完整预处理管道"):
            try:
                # 验证输入参数
                validation_errors = self._validate_inputs(input_json_path, output_dir)
                if validation_errors:
                    raise ValueError(f"输入验证失败: {validation_errors}")
                
                # 确保输出目录存在
                ensure_directory(output_dir)
                
                # 构建文件路径
                paths = self._build_file_paths(input_json_path, output_dir)
                
                # 执行处理步骤
                results = {}
                
                # 步骤1: JSON转Markdown
                if self.config.json_to_md_enabled:
                    results['json_to_md'] = self._step_json_to_markdown(
                        input_json_path, paths['md_file']
                    )
                else:
                    self.logger.info("跳过JSON转Markdown步骤")
                    results['json_to_md'] = {"status": "skipped"}
                
                # 步骤2: 图片链接转换
                if self.config.image_link_conversion_enabled:
                    results['image_conversion'] = self._step_image_conversion(
                        paths['md_file'], paths['images_dir']
                    )
                else:
                    self.logger.info("跳过图片链接转换步骤")
                    results['image_conversion'] = {"status": "skipped"}
                
                # 步骤3: 图片文本检测
                if self.config.text_detection_enabled:
                    results['text_detection'] = self._step_text_detection(
                        paths['md_file'], paths['images_dir']
                    )
                else:
                    self.logger.info("跳过图片文本检测步骤")
                    results['text_detection'] = {"status": "skipped"}
                
                # 生成处理报告
                report = self._generate_report(results, paths)
                
                # 保存处理报告
                report_path = Path(output_dir) / "preprocess_report.json"
                with open(report_path, 'w', encoding='utf-8') as f:
                    json.dump(report, f, indent=2, ensure_ascii=False)
                
                self.logger.info(f"预处理完成，报告已保存: {report_path}")
                return report
                
            except Exception as e:
                self.logger.error(f"预处理管道执行失败: {e}")
                self.stats.add_failure(str(e))
                raise
            finally:
                self.stats.finish()
    
    def run_single_step(self, step_name: str, **kwargs) -> Dict[str, Any]:
        """
        运行单个处理步骤（用于调试和测试）
        
        Args:
            step_name: 步骤名称 ('json_to_md', 'image_conversion', 'text_detection')
            **kwargs: 步骤参数
        
        Returns:
            处理结果字典
        """
        self.logger.info(f"运行单个步骤: {step_name}")
        
        if step_name == 'json_to_md':
            return self.json_processor.process(
                kwargs['input_json_path'], 
                kwargs['output_md_path']
            )
        elif step_name == 'image_conversion':
            return self.image_converter.process(
                kwargs['md_file_path'], 
                kwargs['images_dir']
            )
        elif step_name == 'text_detection':
            return self.text_detector.process(
                kwargs['md_file_path'], 
                kwargs['images_dir']
            )
        else:
            raise ValueError(f"未知的步骤名称: {step_name}")
    
    def _validate_inputs(self, input_json_path: str, output_dir: str) -> List[str]:
        """验证输入参数"""
        errors = []
        
        # 验证配置
        config_errors = self.config.validate()
        errors.extend(config_errors)
        
        # 验证路径
        paths = {
            "输入JSON文件": input_json_path,
            "输出目录": output_dir
        }
        path_errors = validate_paths(paths)
        errors.extend(path_errors)
        
        return errors
    
    def _build_file_paths(self, input_json_path: str, output_dir: str) -> Dict[str, str]:
        """构建处理过程中需要的文件路径"""
        input_path = Path(input_json_path)
        output_path = Path(output_dir)
        
        # 基础文件名（不含扩展名）
        base_name = input_path.stem
        
        paths = {
            'md_file': str(output_path / f"{base_name}_preprocessed.md"),
            'images_dir': str(output_path.parent / f"{base_name}_temp_images"),
            'backup_dir': str(output_path / "backups"),
            'config_file': str(output_path / "preprocess_config.json")
        }
        
        # 保存配置文件
        ensure_directory(output_dir)
        self.config.to_json(paths['config_file'])
        
        return paths
    
    def _step_json_to_markdown(self, input_json_path: str, output_md_path: str) -> Dict[str, Any]:
        """执行JSON转Markdown步骤"""
        self.logger.info("步骤1: JSON转Markdown")
        
        try:
            result = self.json_processor.process(input_json_path, output_md_path)
            self.stats.add_success()
            self.stats.increment_files()
            return result
        except Exception as e:
            self.logger.error(f"JSON转Markdown失败: {e}")
            self.stats.add_failure(f"JSON转Markdown失败: {e}")
            raise
    
    def _step_image_conversion(self, md_file_path: str, images_dir: str) -> Dict[str, Any]:
        """执行图片链接转换步骤"""
        self.logger.info("步骤2: 图片链接转换")
        
        try:
            result = self.image_converter.process(md_file_path, images_dir)
            self.stats.add_success()
            return result
        except Exception as e:
            self.logger.error(f"图片链接转换失败: {e}")
            self.stats.add_failure(f"图片链接转换失败: {e}")
            raise
    
    def _step_text_detection(self, md_file_path: str, images_dir: str) -> Dict[str, Any]:
        """执行图片文本检测步骤"""
        self.logger.info("步骤3: 图片文本检测")
        
        try:
            result = self.text_detector.process(md_file_path, images_dir)
            self.stats.add_success()
            return result
        except Exception as e:
            self.logger.error(f"图片文本检测失败: {e}")
            self.stats.add_failure(f"图片文本检测失败: {e}")
            raise
    
    def _generate_report(self, results: Dict[str, Any], paths: Dict[str, str]) -> Dict[str, Any]:
        """生成处理报告"""
        # 收集所有处理器的统计信息
        processor_stats = {
            'json_processor': self.json_processor.get_stats(),
            'image_converter': self.image_converter.get_stats(),
            'text_detector': self.text_detector.get_stats()
        }
        
        # 计算总体统计
        total_stats = {
            'total_files_processed': sum(s['processed_files'] for s in processor_stats.values()),
            'total_successful_operations': sum(s['successful_operations'] for s in processor_stats.values()),
            'total_failed_operations': sum(s['failed_operations'] for s in processor_stats.values()),
            'total_errors': sum(len(s['errors']) for s in processor_stats.values())
        }
        
        report = {
            'experiment_info': {
                'experiment_name': self.config.experiment_name,
                'config': self.config.to_dict(),
                'ablation_config': self.config.ablation_config
            },
            'processing_results': results,
            'file_paths': paths,
            'processor_statistics': processor_stats,
            'total_statistics': total_stats,
            'pipeline_statistics': self.stats.to_dict(),
            'summary': self.stats.summary()
        }
        
        return report
    
    def get_experiment_results(self) -> Dict[str, Any]:
        """获取实验结果（用于消融实验）"""
        return {
            'experiment_name': self.config.experiment_name,
            'config': self.config.to_dict(),
            'statistics': self.stats.to_dict(),
            'processor_stats': {
                'json_processor': self.json_processor.get_stats(),
                'image_converter': self.image_converter.get_stats(),
                'text_detector': self.text_detector.get_stats()
            }
        }


class BatchPreprocessPipeline:
    """批量预处理管道"""
    
    def __init__(self, config: PreprocessConfig):
        self.config = config
        self.logger = setup_logging(
            log_level=config.log_level,
            log_file=config.log_file_path if config.log_to_file else None,
            logger_name="BatchPreprocessPipeline"
        )
    
    def run_batch(self, input_files: List[str], output_base_dir: str) -> Dict[str, Any]:
        """
        批量处理多个文件
        
        Args:
            input_files: 输入文件路径列表
            output_base_dir: 输出基础目录
        
        Returns:
            批量处理结果
        """
        self.logger.info(f"开始批量处理 {len(input_files)} 个文件")
        
        batch_results = []
        failed_files = []
        
        for i, input_file in enumerate(input_files, 1):
            try:
                self.logger.info(f"处理文件 {i}/{len(input_files)}: {input_file}")
                
                # 为每个文件创建独立的输出目录
                file_name = Path(input_file).stem
                output_dir = Path(output_base_dir) / file_name
                
                # 创建单独的管道实例
                pipeline = PreprocessPipeline(self.config)
                result = pipeline.run(input_file, str(output_dir))
                
                batch_results.append({
                    'input_file': input_file,
                    'output_dir': str(output_dir),
                    'result': result,
                    'status': 'success'
                })
                
            except Exception as e:
                self.logger.error(f"处理文件失败 {input_file}: {e}")
                failed_files.append(input_file)
                batch_results.append({
                    'input_file': input_file,
                    'error': str(e),
                    'status': 'failed'
                })
        
        # 生成批量处理报告
        batch_report = {
            'total_files': len(input_files),
            'successful_files': len(input_files) - len(failed_files),
            'failed_files': len(failed_files),
            'failed_file_list': failed_files,
            'results': batch_results,
            'config': self.config.to_dict()
        }
        
        # 保存批量报告
        report_path = Path(output_base_dir) / "batch_preprocess_report.json"
        ensure_directory(output_base_dir)
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(batch_report, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"批量处理完成，报告已保存: {report_path}")
        return batch_report


class AblationExperimentRunner:
    """消融实验运行器"""
    
    def __init__(self, base_config: PreprocessConfig, experiment_configs: List[str]):
        self.base_config = base_config
        self.experiment_configs = experiment_configs
        self.logger = setup_logging(logger_name="AblationExperimentRunner")
    
    def run_experiments(self, input_json_path: str, output_base_dir: str) -> Dict[str, Any]:
        """
        运行消融实验
        
        Args:
            input_json_path: 输入JSON文件路径
            output_base_dir: 输出基础目录
        
        Returns:
            实验结果汇总
        """
        self.logger.info(f"开始消融实验，共 {len(self.experiment_configs)} 个配置")
        
        experiment_results = []
        
        for config_name in self.experiment_configs:
            try:
                self.logger.info(f"运行实验: {config_name}")
                
                # 创建实验配置
                config = PreprocessConfig()
                config.apply_ablation(config_name)
                config.base_dir = self.base_config.base_dir
                config.output_dir = self.base_config.output_dir
                
                # 创建实验输出目录
                experiment_dir = Path(output_base_dir) / f"experiment_{config_name}"
                
                # 运行实验
                pipeline = PreprocessPipeline(config)
                result = pipeline.run(input_json_path, str(experiment_dir))
                
                experiment_results.append({
                    'experiment_name': config_name,
                    'config': config.to_dict(),
                    'result': result,
                    'output_dir': str(experiment_dir),
                    'status': 'success'
                })
                
            except Exception as e:
                self.logger.error(f"实验失败 {config_name}: {e}")
                experiment_results.append({
                    'experiment_name': config_name,
                    'error': str(e),
                    'status': 'failed'
                })
        
        # 生成实验汇总报告
        summary_report = {
            'total_experiments': len(self.experiment_configs),
            'successful_experiments': len([r for r in experiment_results if r['status'] == 'success']),
            'failed_experiments': len([r for r in experiment_results if r['status'] == 'failed']),
            'experiment_results': experiment_results,
            'base_config': self.base_config.to_dict()
        }
        
        # 保存汇总报告
        report_path = Path(output_base_dir) / "ablation_experiment_summary.json"
        ensure_directory(output_base_dir)
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(summary_report, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"消融实验完成，汇总报告已保存: {report_path}")
        return summary_report 