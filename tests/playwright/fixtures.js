const base = require("@playwright/test");
const {MD5} = require("crypto-js");

const credentials = {
    username: process.env.OCTOPRINT_USERNAME || "admin",
    password: process.env.OCTOPRINT_PASSWORD || "test",
    apikey: process.env.OCTOPRINT_APIKEY || "yo5a103LN7co50R4_IAeLvGoLm08BpdfvKngzfHPcPE"
};

const mfaCredentials = {
    username: process.env.OCTOPRINT_MFA_USERNAME || "mfa",
    password: process.env.OCTOPRINT_MFA_PASSWORD || "mfa",
    apikey: process.env.OCTOPRINT_APIKEY || "yo5a103LN7co50R4_IAeLvGoLm08BpdfvKngzfHPcPE",
    token: "secret"
};

const defaultHeaders = {
    "X-OctoPrint-Api-Version": "1.12.0"
};

const expect = base.expect;

exports.test = base.test.extend({
    loginApi: async ({context, baseURL}, use) => {
        const loginApi = {
            login: async (username, password, remember) => {
                return await context.request.post(baseURL + "/api/login", {
                    data: {
                        user: username,
                        pass: password,
                        remember: !!remember
                    },
                    headers: defaultHeaders
                });
            },

            logout: async () => {
                return await context.request.post(baseURL + "/api/logout", {
                    headers: defaultHeaders
                });
            },

            loginDefault: async (remember) => {
                const response = await loginApi.login(
                    credentials.username,
                    credentials.password,
                    remember
                );
                await expect(response.ok()).toBeTruthy();
                return response;
            }
        };

        await use(loginApi);
    },

    connectionApi: async ({context, baseURL}, use) => {
        const connect = async (connector, parameters) => {
            connector = connector || "serial";
            parameters = parameters || {port: "AUTO", baudrate: 0};
            return await context.request.post(baseURL + "/api/connection", {
                data: {
                    command: "connect",
                    connector: connector,
                    parameters: parameters
                },
                headers: defaultHeaders
            });
        };
        const disconnect = async () => {
            return await context.request.post(baseURL + "/api/connection", {
                data: {
                    command: "disconnect"
                },
                headers: defaultHeaders
            });
        };

        const connectionApi = {
            connect: connect,
            disconnect: disconnect,
            ensureConnected: async (connector, parameters) => {
                const response = await context.request.get(baseURL + "/api/connection", {
                    headers: defaultHeaders
                });
                const data = await response.json();
                if (
                    data.current.state === "Operational" &&
                    (!connector || data.current.connector === connector) &&
                    (!parameters ||
                        (data.current.parameters &&
                            Object.keys(parameters).every(
                                (key) => parameters[key] === data.current.parameters[key]
                            )))
                ) {
                    return;
                }
                await disconnect();
                await connect(connector, parameters);
            }
        };
        await use(connectionApi);
    },

    filesApi: async ({context, baseURL}, use) => {
        const filesApi = {
            ensureFileUnknown: async (location, name) => {
                return await context.request.delete(
                    baseURL + `/api/files/${location}/${name}`,
                    {headers: defaultHeaders}
                );
            },
            getEntryId: (origin, path) => {
                path = path.replace(/^\/+/, "");
                return MD5(`${origin}:${path}`);
            }
        };
        await use(filesApi);
    },

    credentials: async ({}, use) => {
        await use(credentials);
    },

    mfaCredentials: async ({}, use) => {
        await use(mfaCredentials);
    },

    ui: async ({page, util, loginApi, baseURL}, use) => {
        const ui = {
            gotoLogin: async () => {
                await page.goto(baseURL + "/?l10n=en");
                await ui.loginHasLoaded();
            },

            gotoCore: async () => {
                await page.goto(baseURL + "/?l10n=en");
                await ui.coreHasLoaded();
            },

            gotoLoggedInCore: async () => {
                await loginApi.loginDefault();
                await page.goto(baseURL + "/?l10n=en");
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

                const loginForm = await page.getByTestId("login-form");
                await expect(loginForm).toBeVisible();

                const loginTitle = await page.getByTestId("login-title");
                await expect(loginTitle).toBeVisible();
                await expect(loginTitle).toContainText("Please log in");
            },

            mfaHasLoaded: async () => {
                await ui.loginIsLoading();
                await page.waitForFunction(
                    () =>
                        window.OctoPrint &&
                        window.OctoPrint.loginui &&
                        window.OctoPrint.loginui.startedUp,
                    {timeout: 10_000}
                );

                const mfaForm = await page.getByTestId("mfa-form");
                await expect(mfaForm).toBeVisible();
            }
        };
        await use(ui);
    },

    util: async ({context, baseURL}, use) => {
        const getCookieName = (cookie) => {
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
        };

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

            getCookieName: getCookieName,

            setCookie: async (name, value) => {
                const cookieName = getCookieName(name);
                await context.addCookies([
                    {name: cookieName, value: value, url: baseURL}
                ]);
            },

            deleteCookie: async (name) => {
                const cookieName = getCookieName(name);
                await context.clearCookies({name: cookieName});
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
