import logging

from . import CheckResult, HealthCheck, Result


class GttUnusableCheck(HealthCheck):
    key = "gtt_unusable"

    def perform_check(self, force: bool = False) -> CheckResult:
        try:
            import gcode_thumbnail_tool  # noqa: F401

            return CheckResult(result=Result.OK, context={})
        except ImportError as exc:
            logging.getLogger(__name__).exception(
                "GCODE Thumbnail Tool unavailable due to ImportError"
            )
            return CheckResult(result=Result.INFO, context={"exc": str(exc)})
