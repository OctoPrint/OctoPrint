from . import CheckResult, HealthCheck, Result


class GlobalApiKeyCheck(HealthCheck):
    key = "global_api_key"

    def perform_check(self, force: bool = False) -> CheckResult:
        from octoprint.settings import settings as s

        return CheckResult(
            result=Result.WARNING if s().get(["api", "key"]) else Result.OK,
            context={},
        )
