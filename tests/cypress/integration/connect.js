import {prepare_server, login, disconnect, await_coreui} from "../util/util";

context("Connection test against virtual printer", () => {
    const username = "admin";
    const password = "test";

    beforeEach(() => {
        prepare_server();

        // login
        login(username, password);

        // ensure we are disconnected
        disconnect();

        cy.visit("/");
        await_coreui();
    });

    it("connect & disconnect", () => {
        cy.get("[data-test-id=state-string]", {timeout: 10000}).should(
            "contain",
            "Offline"
        );

        cy.get("[data-test-id=connection-printer-profiles]").should(
            "have.length.greaterThan",
            0
        );
        cy.get("[data-test-id=connection-ports]").select("VIRTUAL");
        cy.get("[data-test-id=connection-baudrates]").select("AUTO");
        cy.get("[data-test-id=connection-connect]").should("contain", "Connect").click();

        cy.wait(["@connectionCommand", "@connectionDetails"]);
        cy.get("[data-test-id=sidebar-connection-content]", {timeout: 10000}).should(
            "not.be.visible"
        );
        cy.get("[data-test-id=state-string]").should("contain", "Operational");

        cy.get("[data-test-id=sidebar-connection-toggle]").click();
        cy.get("[data-test-id=connection-connect]")
            .should("be.visible")
            .should("contain", "Disconnect")
            .click();

        cy.wait(["@connectionCommand", "@connectionDetails"]);
        cy.get("[data-test-id=state-string]").should("contain", "Offline");
    });
});
