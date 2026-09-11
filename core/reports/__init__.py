"""
Report generation module for PLUTO v2.
Generate professional reports in multiple formats.
"""

from .generator import ReportGenerator
from .templates.academic import AcademicReport
from .templates.executive import ExecutiveReport
from .templates.news import NewsReport
from .templates.comparison import ComparisonReport
from .templates.technical import TechnicalReport
from .templates.data_analysis import DataAnalysisReport

__all__ = [
    'ReportGenerator',
    'AcademicReport',
    'ExecutiveReport',
    'NewsReport',
    'ComparisonReport',
    'TechnicalReport',
    'DataAnalysisReport',
]
