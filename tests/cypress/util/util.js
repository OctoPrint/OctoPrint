export const prepare_server = () => {
    cy.intercept("POST", get_full_url("/api/login")).as("login");
    cy.intercept("POST", get_full_url("/api/logout")).as("logout");
    cy.intercept("GET", get_full_url("/api/settings")).as("settings");
    cy.intercept("GET", get_full_url("/api/files?recursive=true")).as("files");
    cy.intercept("GET", get_full_url("/plugin/softwareupdate/check")).as(
        "softwareupdate"
    );
    cy.intercept("GET", get_full_url("/plugin/pluginmanager/plugins")).as(
        "pluginmanager"
    );
    cy.intercept("POST", get_full_url("/api/connection")).as("connectionCommand");
    cy.intercept("GET", get_full_url("/api/connection")).as("connectionDetails");
};

export const await_loginui = () => {
    cy.get("[data-test-id=login-title]")
        .should("be.visible")
        .should("contain", "Please log in");
    cy.window().its("OctoPrint.loginui.startedUp", {timeout: 30000}).should("be.true");
};

export const await_coreui = () => {
    cy.wait(["@login", "@settings", "@files", "@softwareupdate", "@pluginmanager"]);
    cy.window().its("OctoPrint.coreui.startedUp", {timeout: 30000}).should("be.true");
};

export const login = (username, password) => {
    cy.request({
        method: "POST",
        url: get_full_url("/api/login"),
        body: {
            user: username,
            pass: password
        }
    });
};

export const logout = () => {
    cy.request({
        method: "POST",
        url: get_full_url("/api/logout")
    });
};

export const connect = (port, baudrate) => {
    port = port || "AUTO";
    baudrate = baudrate || 0;
    cy.request({
        method: "POST",
        url: get_full_url("/api/connection"),
        body: {
            command: "connect",
            port: port,
            baudrate: baudrate
        }
    });
};

export const disconnect = () => {
    cy.request({
        method: "POST",
        url: get_full_url("/api/connection"),
        body: {
            command: "disconnect"
        }
    });
};

export const ensure_file_unknown = (location, name) => {
    cy.request({
        method: "DELETE",
        url: get_full_url(`/api/files/${location}/${name}`),
        failOnStatusCode: false
    });
};

export const get_cookie_name = (cookie) => {
    const url = new URL(Cypress.config("baseUrl"));
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

export const get_full_url = (url) => {
    const parsed = new URL(Cypress.config("baseUrl"));

    let path = "";
    if (parsed.pathname) {
        path = parsed.pathname;
    }
    if (path.endsWith("/")) {
        path = path.substring(0, path.length - 1);
    }

    let url2 = url;
    if (url2.startsWith("/")) {
        url2 = url2.substring(1);
    }

    return path + "/" + url2;
};
