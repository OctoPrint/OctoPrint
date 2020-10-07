import {prepare_server, login, disconnect, await_coreui} from "../util/util";

context("Test settings dialog opens and closes", () => {
    const username = "admin";
    const password = "test";

    beforeEach(() => {
        prepare_server();

        // login
        login(username, password);

        cy.visit("/");
        await_coreui();
    });

    it("opens settings", () => {
        cy.get("[data-test-id=settings-open]").click();
        cy.get("[data-test-id=settings-dialog]").should("be.visible");
    });

    describe("close settings", () => {
        beforeEach(() => {
            cy.get("[data-test-id=settings-open]").click();
            cy.get("[data-test-id=settings-dialog]").should("be.visible");
        });

        it("closes settings via button", () => {
            cy.get("[data-test-id=settings-close-button").click();
        });

        it("closes settings via x", () => {
            cy.get("[data-test-id=settings-close-x").click({force: true});
        });

        it.skip("closes settings via click outside", () => {
            cy.get("body").click();
        });

        it.skip("closes settings via ESC", () => {
            cy.get("[data-test-id=settings-dialog]").trigger("keydown", {
                key: "Escape",
                which: 27,
                code: "Escape"
            });
        });

        afterEach(() => {
            cy.get("[data-test-id=settings-dialog]").should("not.be.visible");
        });
    });
});
