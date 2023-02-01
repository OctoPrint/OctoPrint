// @ts-check
const {test, expect} = require("../fixtures");

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

    test.fixme("by keyboard", async ({page, ui, util, credentials}) => {
        // TODO: this doesn't work yet
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
