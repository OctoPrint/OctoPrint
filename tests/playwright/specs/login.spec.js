// @ts-check
const {test, expect} = require("../fixtures");
const path = require("path");
const fs = require("fs");

test.describe.parallel("Successful login", async () => {
    test.beforeEach(async ({ui}) => {
        await ui.gotoLogin();
    });

    test("basic", async ({page, ui, util, credentials}) => {
        await page.getByTestId("login-username").fill(credentials.username);
        await page.getByTestId("login-password").fill(credentials.password);
        await page.getByTestId("login-submit").click();

        await ui.coreIsLoading();
        await util.loginCookiesWithoutRememberMe();
    });

    test("with remember me", async ({page, ui, util, credentials}) => {
        await page.getByTestId("login-username").fill(credentials.username);
        await page.getByTestId("login-password").fill(credentials.password);
        await page.getByTestId("login-remember-me").check();
        await page.getByTestId("login-submit").click();

        await ui.coreIsLoading();
        await util.loginCookiesWithRememberMe();
    });

    test("by keyboard", async ({page, ui, util, credentials}) => {
        await expect(page.getByTestId("login-username")).toBeFocused();
        await page.getByTestId("login-username").type(credentials.username);

        await page.getByTestId("login-username").press("Tab");
        await expect(page.getByTestId("login-password")).toBeFocused();
        await page.getByTestId("login-password").type(credentials.password);

        await page.getByTestId("login-password").press("Tab");
        await expect(page.getByTestId("login-remember-me")).toBeFocused();
        await page.getByTestId("login-remember-me").press("Space");

        await page.getByTestId("login-remember-me").press("Tab");
        await expect(page.getByTestId("login-submit")).toBeFocused();
        await page.getByTestId("login-submit").press("Enter");

        await ui.coreIsLoading();
        await util.loginCookiesWithRememberMe();
    });
});

test.describe.parallel("Remember Me functionality", async () => {
    const dataDir = ".auth";
    const storageState = path.join(dataDir, "storage-state-login-remember-me.json");

    if (!fs.existsSync(dataDir)) {
        fs.mkdirSync(dataDir);
    }
    if (!fs.existsSync(storageState)) {
        fs.writeFileSync(storageState, "{}");
    }

    test.beforeAll(async ({request, baseURL, credentials}) => {
        await request.post(baseURL + "/api/login", {
            data: {
                user: credentials.username,
                pass: credentials.password,
                remember: true
            }
        });

        await request.storageState({path: storageState});
    });

    test.use({
        storageState: storageState
    });

    test("remember me recognized", async ({page, ui, util, credentials}) => {
        await util.deleteCookie("session");

        await ui.gotoCore();

        await ui.coreHasLoaded();
        await util.loginCookiesWithRememberMe();
        await expect(page.getByTestId("login-menu")).toContainText(credentials.username);
    });

    test("remember me doesn't prevent logout", async ({page, ui, util, credentials}) => {
        await ui.gotoCore();
        await ui.coreHasLoaded();

        await expect(page.getByTestId("login-menu")).toContainText(credentials.username);
        await page.getByTestId("login-menu").click();

        await expect(page.getByTestId("logout-submit")).toBeVisible();
        await page.getByTestId("logout-submit").click();

        await ui.loginIsLoading();
    });
});

test.describe.parallel("Failed login", async () => {
    test.beforeEach(async ({ui}) => {
        await ui.gotoLogin();
    });

    test("wrong user name", async ({page, credentials}) => {
        await page.getByTestId("login-username").fill("idonotexist");
        await page.getByTestId("login-password").fill(credentials.password);
        await page.getByTestId("login-submit").click();
    });

    test("wrong password", async ({page, credentials}) => {
        await page.getByTestId("login-username").fill(credentials.username);
        await page.getByTestId("login-password").fill("wrongpassword");
        await page.getByTestId("login-submit").click();
    });

    test.afterEach(async ({page, ui}) => {
        await ui.loginHasLoaded();

        const loginTitle = page.getByTestId("login-title");
        await expect(loginTitle).toBeVisible();
        await expect(loginTitle).toContainText("Please log in");

        const loginError = page.getByTestId("login-error");
        await expect(loginError).toBeVisible();
        await expect(loginError).toContainText("Incorrect username or password");
    });
});

test("Successful logout", async ({page, ui, credentials}) => {
    await ui.gotoLoggedInCore();

    await expect(page.getByTestId("login-menu")).toContainText(credentials.username);
    await page.getByTestId("login-menu").click();

    await expect(page.getByTestId("logout-submit")).toBeVisible();
    await page.getByTestId("logout-submit").click();

    await ui.loginIsLoading();
});

if (process.env.TEST_MFA) {
    test.describe.parallel("MFA", async () => {
        test.beforeEach(async ({ui, page, mfaCredentials}) => {
            await ui.gotoLogin();

            await page.getByTestId("login-username").fill(mfaCredentials.username);
            await page.getByTestId("login-password").fill(mfaCredentials.password);
            await page.getByTestId("login-submit").click();
        });

        test("correct token", async ({page, ui, util, mfaCredentials}) => {
            await page.getByTestId("mfa-dummy-token").fill(mfaCredentials.token);
            await page.getByTestId("mfa-dummy-submit").click();

            await ui.coreIsLoading();
            await util.loginCookiesWithoutRememberMe();
        });

        test("wrong token", async ({page, ui, util, mfaCredentials}) => {
            await page.getByTestId("mfa-dummy-token").fill("bzzt, wrong");
            await page.getByTestId("mfa-dummy-submit").click();

            await ui.mfaHasLoaded();

            const mfaError = page.getByTestId("mfa-error");
            await expect(mfaError).toBeVisible();
            await expect(mfaError).toContainText("Incorrect token");
        });
    });
}
