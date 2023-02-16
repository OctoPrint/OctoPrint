const base = require("@playwright/test");

const credentials = {
    username: process.env.OCTOPRINT_USERNAME || "admin",
    password: process.env.OCTOPRINT_PASSWORD || "test"
};

const expect = base.expect;

exports.test = base.test.extend({
    loginApi: async ({context}, use) => {
        const loginApi = {
            login: async (username, password) => {
                return await context.request.post("/api/login", {
                    data: {
                        user: username,
                        pass: password
                    }
                });
            },

            logout: async () => {
                return await context.request.post("/api/logout");
            },

            loginDefault: async () => {
                const response = await loginApi.login(
                    credentials.username,
                    credentials.password
                );
                await expect(response.ok()).toBeTruthy();
                return response;
            }
        };

        await use(loginApi);
    },

    connectionApi: async ({context}, use) => {
        const connectionApi = {
            connect: async (port, baudrate) => {
                port = port || "AUTO";
                baudrate = baudrate || 0;
                return await context.request.post("/api/connection", {
                    data: {
                        command: "connect",
                        port: port,
                        baudrate: baudrate
                    }
                });
            },

            disconnect: async () => {
                return await context.request.post("/api/connection", {
                    data: {
                        command: "disconnect"
                    }
                });
            }
        };
        await use(connectionApi);
    },

    filesApi: async ({context}, use) => {
        const filesApi = {
            ensureFileUnknown: async (location, name) => {
                return await context.request.delete(`/api/files/${location}/${name}`);
            }
        };
        await use(filesApi);
    },

    credentials: async ({}, use) => {
        await use(credentials);
    },

    ui: async ({page, util, loginApi}, use) => {
        const ui = {
            gotoLogin: async () => {
                await page.goto("/?l10n=en");
                await ui.loginHasLoaded();
            },

            gotoLoggedInCore: async () => {
                await loginApi.loginDefault();
                await page.goto("/?l10n=en");
                await ui.coreHasLoaded();
            },

            coreIsLoading: async () => {
                await expect(page).toHaveURL(util.getFullUrlRegExp("/"), {
                    timeout: 15_000
                });
            },

            coreHasLoaded: async () => {
                await ui.coreIsLoading();
                await page.waitForFunction(
                    () =>
                        window.OctoPrint &&
                        window.OctoPrint.coreui &&
                        window.OctoPrint.coreui.startedUp,
                    {timeout: 10_000}
                );
            },

            loggedInCoreHasLoaded: async (username) => {
                username = username || credentials.username;
                await ui.coreHasLoaded();
                await expect(page.getByTestId("login-menu-title")).toContainText(
                    username
                );
            },

            loginIsLoading: async () => {
                await expect(page).toHaveURL(util.getFullUrlRegExp("/login/"), {
                    timeout: 15_000
                });
            },

            loginHasLoaded: async () => {
                await ui.loginIsLoading();
                await page.waitForFunction(
                    () =>
                        window.OctoPrint &&
                        window.OctoPrint.loginui &&
                        window.OctoPrint.loginui.startedUp,
                    {timeout: 10_000}
                );
                const loginTitle = await page.getByTestId("login-title");
                await expect(loginTitle).toBeVisible();
                await expect(loginTitle).toContainText("Please log in");
            }
        };
        await use(ui);
    },

    util: async ({context, baseURL}, use) => {
        const util = {
            loginCookiesWithoutRememberMe: async () => {
                const cookies = await context.cookies();
                const sessionCookie = util.getCookieName("session", baseURL);
                const rememberMeCookie = util.getCookieName("remember_token", baseURL);
                await expect(
                    cookies.find((element) => element.name == sessionCookie)
                ).toBeTruthy();
                await expect(
                    cookies.find((element) => element.name == rememberMeCookie)
                ).toBeFalsy();
            },

            loginCookiesWithRememberMe: async () => {
                const cookies = await context.cookies();
                const sessionCookie = util.getCookieName("session", baseURL);
                const rememberMeCookie = util.getCookieName("remember_token", baseURL);
                await expect(
                    cookies.find((element) => element.name == sessionCookie)
                ).toBeTruthy();
                await expect(
                    cookies.find((element) => element.name == rememberMeCookie)
                ).toBeTruthy();
            },

            getCookieName: (cookie) => {
                const url = new URL(baseURL);
                const port = url.port || (url.protocol === "https:" ? 443 : 80);
                if (url.pathname && url.pathname !== "/") {
                    let path = url.pathname;
                    if (path.endsWith("/")) {
                        path = path.substring(0, path.length - 1);
                    }
                    return `${cookie}_P${port}_R${path.replace(/\//, "|")}`;
                } else {
                    return `${cookie}_P${port}`;
                }
            },

            getFullUrlRegExp: (path) => {
                const fullUrl = baseURL + path;
                const escaped = fullUrl.replace(/[/\-\\^$*+?.()|[\]{}]/g, "\\$&");
                return new RegExp("^" + escaped + "(\\?.*)?(#.*)?$");
            }
        };
        await use(util);
    }
});

exports.expect = expect;
