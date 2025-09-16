# preprocessing_module/pipeline.py

"""
Orchestrates the preprocessing workflow by chaining together individual processors.

This module defines the pipelines that manage the execution flow:
- PreprocessPipeline: Handles the end-to-end processing of a single document.
- BatchPreprocessPipeline: Manages the processing of multiple documents.
- AblationExperimentRunner: Facilitates running and comparing different
  processing configurations for research purposes.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import PreprocessConfig
from .processors import ImageLinkConverter, ImageTextDetector, JsonToMarkdownProcessor
from .utils import (ProcessingStats, ensure_directory, setup_logging,
                    timing_context, validate_paths)


class PreprocessPipeline:
    """Manages the sequential execution of preprocessing steps for a single file."""

    def __init__(self, config: PreprocessConfig):
        self.config = config
        self.logger = setup_logging(
            log_level=config.log_level,
            log_file=config.log_file_path,
            logger_name="PreprocessPipeline",
        )
        self.stats = ProcessingStats()
        
        # Initialize processors
        self.json_processor = JsonToMarkdownProcessor(config, self.logger)
        self.image_converter = ImageLinkConverter(config, self.logger)
        self.text_detector = ImageTextDetector(config, self.logger)
        self.logger.info(f"Pipeline initialized for experiment: {config.experiment_name}")

    def run(self, input_json_path: str, output_dir: str) -> Dict[str, Any]:
        """
        Executes the full preprocessing pipeline on a single JSON file.

        Args:
            input_json_path: Path to the source JSON file.
            output_dir: The directory to store all output files.

        Returns:
            A detailed report of the processing results.
        """
        with timing_context(self.logger, "Entire Preprocessing Pipeline"):
            try:
                self._validate_inputs(input_json_path, output_dir)
                ensure_directory(output_dir)
                paths = self._prepare_paths(input_json_path, output_dir)
                
                results = {}
                # Step 1: JSON to Markdown
                if self.config.json_to_md_enabled:
                    results["json_to_md"] = self.json_processor.process(
                        input_json_path, paths["md_file"]
                    )
                # Step 2: Image Link Conversion
                if self.config.image_link_conversion_enabled:
                    results["image_conversion"] = self.image_converter.process(
                        paths["md_file"], paths["images_dir"]
                    )
                # Step 3: Image Text Detection
                if self.config.text_detection_enabled:
                    results["text_detection"] = self.text_detector.process(
                        paths["md_file"], paths["images_dir"]
                    )

                self.stats.increment_files_processed()
                self.stats.add_success()
                report = self._generate_report(results, paths)
                self._save_report(report, output_dir)
                return report
            except Exception as e:
                self.logger.error(f"Pipeline execution failed: {e}", exc_info=True)
                self.stats.add_failure(str(e))
                raise

    def _validate_inputs(self, input_json: str, output_dir: str) -> None:
        """Validates configuration and paths before execution."""
        errors = self.config.validate()
        errors.extend(validate_paths({"Input JSON": input_json, "Output Dir": output_dir}))
        if errors:
            raise ValueError("Input validation failed: " + "; ".join(errors))

    def _prepare_paths(self, input_json: str, output_dir: str) -> Dict[str, str]:
        """Builds and returns a dictionary of necessary file paths."""
        json_path = Path(input_json)
        base_name = json_path.stem
        
        images_dir = self._find_images_directory(base_name, json_path.parent)
        
        paths = {
            "md_file": str(Path(output_dir) / f"{base_name}_preprocessed.md"),
            "images_dir": str(images_dir),
            "config_file": str(Path(output_dir) / "preprocess_config.json"),
        }
        self.config.to_json(paths["config_file"])
        return paths

    def _find_images_directory(self, base_name: str, search_dir: Path) -> Path:
        """Automatically searches for the corresponding image directory."""
        if self.config.main_images_dir and self.config.auto_search_images:
            main_images_path = Path(self.config.main_images_dir)
            if main_images_path.is_dir():
                for pattern in self.config.image_folder_patterns:
                    folder_name = pattern.format(base_name=base_name)
                    candidate_path = main_images_path / folder_name
                    if candidate_path.is_dir():
                        self.logger.info(f"Found matching image directory: {candidate_path}")
                        return candidate_path
        
        # Fallback to a default directory relative to the input JSON
        default_path = search_dir / f"{base_name}_temp_images"
        self.logger.info(f"Using default image directory: {default_path}")
        return default_path

    def _generate_report(self, results: Dict, paths: Dict) -> Dict[str, Any]:
        """Compiles a final report from all processor statistics."""
        self.stats.finish()
        return {
            "experiment_name": self.config.experiment_name,
            "pipeline_summary": self.stats.summary(),
            "pipeline_stats": self.stats.to_dict(),
            "step_results": results,
            "file_paths": paths,
            "processor_stats": {
                "json_processor": self.json_processor.get_stats(),
                "image_converter": self.image_converter.get_stats(),
                "text_detector": self.text_detector.get_stats(),
            },
        }

    def _save_report(self, report: Dict, output_dir: str) -> None:
        """Saves the final report to a JSON file."""
        report_path = Path(output_dir) / "preprocess_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            # Convert Path objects to strings for JSON serialization
            def make_serializable(obj):
                if isinstance(obj, Path):
                    return str(obj)
                return obj
            json.dump(report, f, indent=2, ensure_ascii=False, default=make_serializable)
        self.logger.info(f"Processing report saved to: {report_path}")

class BatchPreprocessPipeline:
    """Manages batch processing of multiple files."""

    def __init__(self, config: PreprocessConfig):
        self.config = config
        self.logger = setup_logging(
            log_level=config.log_level,
            log_file=config.log_file_path,
            logger_name="BatchPipeline",
        )

    def run_batch(self, input_files: List[str], output_base_dir: str) -> Dict[str, Any]:
        """
        Processes a list of input files in batch mode.

        Args:
            input_files: A list of paths to input JSON files.
            output_base_dir: The root directory for all outputs.

        Returns:
            A summary report of the batch processing task.
        """
        self.logger.info(f"Starting batch processing for {len(input_files)} files.")
        batch_results = []
        
        for file_path in input_files:
            try:
                output_dir = Path(output_base_dir) / Path(file_path).stem
                pipeline = PreprocessPipeline(self.config)
                report = pipeline.run(file_path, str(output_dir))
                batch_results.append({"input_file": file_path, "status": "success", "report": report})
            except Exception as e:
                self.logger.error(f"Failed to process {file_path}: {e}")
                batch_results.append({"input_file": file_path, "status": "failed", "error": str(e)})
        
        return self._generate_batch_report(batch_results, output_base_dir)

    def _generate_batch_report(self, results: List[Dict], out_dir: str) -> Dict[str, Any]:
        """Generates and saves a final report for the batch job."""
        success_count = sum(1 for r in results if r["status"] == "success")
        report = {
            "total_files": len(results),
            "successful_files": success_count,
            "failed_files": len(results) - success_count,
            "results": results,
        }
        report_path = Path(out_dir) / "batch_preprocess_report.json"
        ensure_directory(out_dir)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        self.logger.info(f"Batch processing complete. Report saved to: {report_path}")
        return report

# The AblationExperimentRunner can be kept as is, with translations applied to its logs.
# For brevity, its refactored code is omitted here but follows the same principles.