from . import CheckResult, HealthCheck, Result


class FilesystemStorageCheck(HealthCheck):
    key = "filesystem_storage"

    def perform_check(self, force: bool = False) -> CheckResult:
        import shutil

        from octoprint.settings import default_settings
        from octoprint.settings import settings as s

        settings = s()

        result = Result.OK
        context = {}
        for folder in default_settings.get("folder", {}).keys():
            path = settings.getBaseFolder(
                folder, allow_fallback=False, check_writable=False
            )
            usage = shutil.disk_usage(path)
            usable = usage.used + usage.free
            percent = round(usage.used / usable * 100, 1) if usable else 0.0
            context[folder] = percent

            if percent > self._settings.get("issue_threshold", 95):
                result = Result.ISSUE
            elif percent > self._settings.get("warning_threshold", 80):
                result = Result.WARNING

        return CheckResult(result=result, context=context)
