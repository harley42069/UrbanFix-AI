"""UrbanFix service package.

Keep this module import-light to avoid loading heavy ML libraries at package
import time. Import concrete service modules directly where needed.
"""

def get_detection_service():
	from .detection import get_detection_service as _fn

	return _fn()


def get_image_generation_service():
	from .image_generation import get_image_generation_service as _fn

	return _fn()


def get_cost_estimation_service():
	from .cost_estimation import get_cost_estimation_service as _fn

	return _fn()


def get_audio_generation_service():
	from .audio_generation import get_audio_generation_service as _fn

	return _fn()


def get_video_generation_service():
	from .video_generation import get_video_generation_service as _fn

	return _fn()


def get_pdf_report_service():
	from .pdf_report import get_pdf_report_service as _fn

	return _fn()


def get_orchestrator_service():
	from .orchestrator import get_orchestrator_service as _fn

	return _fn()


__all__ = [
	"get_detection_service",
	"get_image_generation_service",
	"get_cost_estimation_service",
	"get_audio_generation_service",
	"get_video_generation_service",
	"get_pdf_report_service",
	"get_orchestrator_service",
]
