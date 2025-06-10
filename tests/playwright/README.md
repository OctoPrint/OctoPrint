# 🎭️ OctoPrint's E2E Test Suite

This is OctoPrint's [Playwright](https://playwright.dev/) based E2E test suite.

It currently tests the following:

- working login/logout, correct handling of wrong credentials, login with MFA (if enabled)
- connect & disconnect against the virtual printer
- opening and closing the settings
- uploading a basic `gcode` file
- error free page load

Unless `NO_SERVER` is set, the test suite will ensure an OctoPrint server is running by
testing against `http://127.0.0.1:5000/online.txt` and starting the server via
`octoprint [-b $OCTOPRINT_SERVER_BASE] serve --host 127.0.0.1 --port 5000` as needed.

## Requirements

The test suite requires the server to have the following configuration:

- `devel.enableRateLimiter: false` in `config.yaml`
- `devel.enableCsrfProtection: false` in `config.yaml` (unless for `@csrf` tagged tests)
- `plugins.virtual_printer.enabled: true` in `config.yaml`
- `csrf_test` plugin installed (see `.github/fixtures/csrf_test.py`)
- admin account `admin` with password `test` and api key `yo5a103LN7co50R4_IAeLvGoLm08BpdfvKngzfHPcPE` (alternatively `OCTOPRINT_USERNAME`, `OCTOPRINT_PASSWORD` and `OCTOPRINT_APIKEY` need to be configured)
- first run completed, all wizards seen
- if MFA tests are enabled:
  - `mfa_dummy` plugin installed (see `.github/fixtures/mfa_dummy`)
  - user account `mfa` with password `test` and api key `yo5a103LN7co50R4_IAeLvGoLm08BpdfvKngzfHPcPE` (alternatively `OCTOPRINT_MFA_USERNAME`, `OCTOPRINT_MFA_PASSWORD` and `OCTOPRINT_MFA_APIKEY` need to be configured)

A compatible `config.yaml` and `users.yaml` can be found in `.github/fixtures/with_acl`.

## Basic usage

```
npx playwright install
npx playwright test
```

## Configuration

The following environment variables are evaluated:

- `PLAYWRIGHT_BASEURL`: The base URL to test against. Defaults to `http://localhost:5000/online.txt`.
- `OCTOPRINT_SERVER_BASE`: The base folder to use for the OctoPrint server to be started by the test suite. If unset, the default of OctoPrint will be used.
- `NO_SERVER`: If set, no server will be attempted to get started and instead the tests will directly try to run against `PLAYWRIGHT_BASEURL`.
- `TEST_MFA`: If set, the MFA focused tests are enabled. As those require additional configuration and support by the server, they are currently disabled by default.
- `CI`: If set, the `github` reporter will be added to the defined outputs. Additionally, `retries` and `workers` will be set to `2`.
- `OCTOPRINT_USERNAME`, `OCTOPRINT_PASSWORD`: OctoPrint credentials to use for testing, `admin`/`test` by default.
- `OCTOPRINT_MFA_USERNAME`, `OCTOPRINT_MFA_PASSWORD`: OctoPrint credentials to use for MFA testing, `mfa`/`mfa` by default.
