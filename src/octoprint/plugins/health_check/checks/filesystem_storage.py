from . import CheckResult, HealthCheck, Result


class FilesystemStorageCheck(HealthCheck):
    key = "filesystem_storage"

    def perform_check(self, force: bool = False) -> CheckResult:
        import psutil

        from octoprint.settings import default_settings
        from octoprint.settings import settings as s

        settings = s()

        result = Result.OK
        context = {}
        for folder in default_settings.get("folder", {}).keys():
            path = settings.getBaseFolder(
                folder, allow_fallback=False, check_writable=False
            )
            usage = psutil.disk_usage(path)
            context[folder] = usage.percent

            if usage.percent > self._settings.get("issue_threshold", 95):
                result = Result.ISSUE
            elif usage.percent > self._settings.get("warning_threshold", 80):
                result = Result.WARNING

        return CheckResult(result=result, context=context)
