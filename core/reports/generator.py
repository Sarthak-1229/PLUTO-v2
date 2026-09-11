"""
Main report generator for PLUTO v2.
Orchestrates report creation from research results.
"""

import logging
import json
import time
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime
from dataclasses import dataclass, asdict

from core.research.engine import ResearchResult

logger = logging.getLogger(__name__)


@dataclass
class ReportMetadata:
    """Metadata for a generated report."""
    title: str
    subtitle: str
    author: str
    date: str
    sources_count: int
    word_count: int
    read_time_minutes: int
    tags: List[str]
    confidence: float
    verified: bool
    report_type: str


class ReportGenerator:
    """Generate professional reports from research results."""

    def __init__(self, reports_dir: str = "reports"):
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.templates = {
            'academic': None,  # Lazy load
            'executive': None,
            'news': None,
            'comparison': None,
            'technical': None,
            'data_analysis': None,
        }

    def generate(self, result: ResearchResult, query: str, report_type: str = 'auto') -> Dict:
        """
        Generate a comprehensive report.

        Args:
            result: ResearchResult from the research engine
            query: Original user query
            report_type: Type of report ('auto', 'academic', 'executive', 'news', 'comparison', 'technical', 'data_analysis')

        Returns:
            Dictionary with report path, metadata, and content
        """
        logger.info(f"Generating {report_type} report for: {query}")

        # Determine report type if auto
        if report_type == 'auto':
            report_type = self._detect_report_type(result, query)

        # Generate report content
        content = self._generate_content(result, query, report_type)

        # Create metadata
        metadata = self._create_metadata(result, query, report_type, content)

        # Save report
        report_path = self._save_report(content, metadata, report_type)

        # Generate exports
        exports = self._generate_exports(content, metadata, report_path)

        return {
            'path': str(report_path),
            'metadata': asdict(metadata),
            'content': content,
            'exports': exports,
            'report_type': report_type
        }

    def _detect_report_type(self, result: ResearchResult, query: str) -> str:
        """Detect appropriate report type based on query and results."""
        query_lower = query.lower()

        # Check for comparison keywords
        if any(kw in query_lower for kw in ['compare', 'vs ', 'versus ', 'difference between', 'which is better']):
            return 'comparison'

        # Check for news keywords
        if any(kw in query_lower for kw in ['news', 'latest', 'today', 'recent', 'current', 'breaking']):
            return 'news'

        # Check for technical keywords
        if any(kw in query_lower for kw in ['how to', 'tutorial', 'guide', 'implementation', 'code', 'programming']):
            return 'technical'

        # Check for data keywords
        if any(kw in query_lower for kw in ['statistics', 'data', 'analysis', 'numbers', 'figures']):
            return 'data_analysis'

        # Default to academic for research queries
        if any(kw in query_lower for kw in ['research', 'study', 'paper', 'academic', 'scientific']):
            return 'academic'

        # Check source types
        if result.sources_used and 'arxiv' in result.sources_used:
            return 'academic'

        # Default
        return 'executive'

    def _generate_content(self, result: ResearchResult, query: str, report_type: str) -> str:
        """Generate report content based on type."""
        # Import templates
        from .templates.academic import AcademicReport
        from .templates.executive import ExecutiveReport
        from .templates.news import NewsReport
        from .templates.comparison import ComparisonReport
        from .templates.technical import TechnicalReport
        from .templates.data_analysis import DataAnalysisReport

        templates = {
            'academic': AcademicReport(),
            'executive': ExecutiveReport(),
            'news': NewsReport(),
            'comparison': ComparisonReport(),
            'technical': TechnicalReport(),
            'data_analysis': DataAnalysisReport(),
        }

        template = templates.get(report_type, ExecutiveReport())
        return template.generate(result, query)

    def _create_metadata(self, result: ResearchResult, query: str, report_type: str, content: str) -> ReportMetadata:
        """Create report metadata."""
        words = content.split()
        return ReportMetadata(
            title=query,
            subtitle=f"{report_type.title()} Report",
            author="PLUTO v2 AI Assistant",
            date=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            sources_count=len(result.documents),
            word_count=len(words),
            read_time_minutes=max(1, len(words) // 200),
            tags=result.sources_used,
            confidence=result.confidence,
            verified=result.verified,
            report_type=report_type
        )

    def _save_report(self, content: str, metadata: ReportMetadata, report_type: str) -> Path:
        """Save report to file."""
        slug = metadata.title.lower().replace(' ', '-').replace('/', '-')[:50]
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        filename = f"{slug}-{timestamp}.md"
        path = self.reports_dir / filename

        # Add metadata header
        header = f"""---
title: "{metadata.title}"
subtitle: "{metadata.subtitle}"
author: "{metadata.author}"
date: "{metadata.date}"
sources: {metadata.sources_count}
words: {metadata.word_count}
read_time: {metadata.read_time_minutes} min
tags: {', '.join(metadata.tags)}
confidence: {metadata.confidence:.2%}
verified: {metadata.verified}
type: {metadata.report_type}
---

# {metadata.title}

**Generated by PLUTO v2 on {metadata.date}**

"""

        full_content = header + content
        path.write_text(full_content, encoding='utf-8')

        logger.info(f"Report saved to: {path}")
        return path

    def _generate_exports(self, content: str, metadata: ReportMetadata, report_path: Path) -> Dict:
        """Generate additional export formats."""
        exports = {}

        # JSON export
        json_path = report_path.with_suffix('.json')
        json_data = {
            'metadata': asdict(metadata),
            'content': content,
            'generated_at': datetime.now().isoformat()
        }
        json_path.write_text(json.dumps(json_data, indent=2), encoding='utf-8')
        exports['json'] = str(json_path)

        # HTML export (basic)
        html_path = report_path.with_suffix('.html')
        html_content = self._content_to_html(content, metadata)
        html_path.write_text(html_content, encoding='utf-8')
        exports['html'] = str(html_path)

        return exports

    def _content_to_html(self, content: str, metadata: ReportMetadata) -> str:
        """Convert markdown content to HTML."""
        import re

        html_lines = ['<!DOCTYPE html>', '<html>', '<head>',
                     '<meta charset="UTF-8">',
                     '<title>{}</title>'.format(metadata.title),
                     '<style>',
                     'body { font-family: system-ui, sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; }',
                     'h1 { color: #1a1a2e; border-bottom: 2px solid #4F46E5; padding-bottom: 10px; }',
                     'h2 { color: #16213e; margin-top: 30px; }',
                     'blockquote { border-left: 4px solid #4F46E5; margin: 0; padding-left: 20px; color: #555; }',
                     'code { background: #f4f4f4; padding: 2px 6px; border-radius: 4px; }',
                     'pre { background: #f4f4f4; padding: 15px; overflow-x: auto; }',
                     'table { border-collapse: collapse; width: 100%; }',
                     'th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }',
                     'th { background: #4F46E5; color: white; }',
                     '</style>',
                     '</head>', '<body>']

        # Simple markdown to HTML conversion
        in_code_block = False
        for line in content.split('\n'):
            if line.startswith('```'):
                in_code_block = not in_code_block
                html_lines.append('<pre><code>')
            elif in_code_block:
                html_lines.append(re.escape(line))
            elif line.startswith('# '):
                html_lines.append(f'<h1>{line[2:]}</h1>')
            elif line.startswith('## '):
                html_lines.append(f'<h2>{line[3:]}</h2>')
            elif line.startswith('### '):
                html_lines.append(f'<h3>{line[4:]}</h3>')
            elif line.startswith('- '):
                html_lines.append(f'<li>{line[2:]}</li>')
            elif line.startswith('> '):
                html_lines.append(f'<blockquote>{line[2:]}</blockquote>')
            elif line.startswith('**') and line.endswith('**'):
                html_lines.append(f'<strong>{line[2:-2]}</strong>')
            elif line.strip():
                html_lines.append(f'<p>{line}</p>')

        html_lines.extend(['</body>', '</html>'])

        # Fix list wrapping
        html_content = '\n'.join(html_lines)
        html_content = html_content.replace('</li>\n<li>', '</li><li>')

        return html_content

    def list_reports(self, limit: int = 10) -> List[Dict]:
        """List available reports."""
        reports = []
        for path in sorted(self.reports_dir.glob('*.md'), reverse=True)[:limit]:
            try:
                content = path.read_text(encoding='utf-8')
                # Extract metadata from frontmatter
                if content.startswith('---'):
                    parts = content.split('---')
                    if len(parts) >= 3:
                        meta_text = parts[1]
                        meta = {}
                        for line in meta_text.strip().split('\n'):
                            if ':' in line:
                                key, value = line.split(':', 1)
                                meta[key.strip()] = value.strip().strip('"')

                        reports.append({
                            'filename': path.name,
                            'title': meta.get('title', path.stem),
                            'date': meta.get('date', ''),
                            'sources': meta.get('sources', '0'),
                            'type': meta.get('type', 'unknown')
                        })
            except Exception as e:
                logger.warning(f"Failed to read report {path}: {e}")

        return reports


# Singleton instance
_generator = None

def get_report_generator() -> ReportGenerator:
    """Get or create the singleton ReportGenerator instance."""
    global _generator
    if _generator is None:
        _generator = ReportGenerator()
    return _generator
