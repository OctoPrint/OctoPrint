export const prepare_server = () => {
    cy.intercept("POST", "/api/login").as("login");
    cy.intercept("POST", "/api/logout").as("logout");
    cy.intercept("GET", "/api/settings").as("settings");
    cy.intercept("GET", "/api/files?recursive=true").as("files");
    cy.intercept("GET", "/plugin/softwareupdate/check").as("softwareupdate");
    cy.intercept("GET", "/plugin/pluginmanager/plugins").as("pluginmanager");
    cy.intercept("POST", "/api/connection").as("connectionCommand");
    cy.intercept("GET", "/api/connection").as("connectionDetails");
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
        url: "/api/login",
        body: {
            user: username,
            pass: password
        }
    });
};

export const logout = () => {
    cy.request({
        method: "POST",
        url: "/api/logout"
    });
};

export const connect = (port, baudrate) => {
    port = port || "AUTO";
    baudrate = baudrate || 0;
    cy.request({
        method: "POST",
        url: "/api/connection",
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
        url: "/api/connection",
        body: {
            command: "disconnect"
        }
    });
};

export const ensure_file_unknown = (location, name) => {
    cy.request({
        method: "DELETE",
        url: `/api/files/${location}/${name}`,
        failOnStatusCode: false
    });
};
