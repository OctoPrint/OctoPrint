describe('Connection test against virtual printer', () => {
    const username = 'admin';
    const password = 'test';

    beforeEach(() => {
        // login
        cy.request({
            method: 'POST',
            url: '/api/login',
            body: {
                "user": username,
                "pass": password
            }
        });

        // ensure we are disconnected
        cy.request({
            method: 'POST',
            url: '/api/connection',
            body: {
                "command": "disconnect"
            }
        });

        cy.visit('/');
        cy.window({timeout: 10000})
            .should('have.nested.property', 'OctoPrint.coreui.startedUp', true);
    });

    it('connect & disconnect', () => {
        cy.get('#state .accordion-inner strong:first')
            .should('contain', 'Offline');

        cy.get('#connection_printers')
            .should('have.length.greaterThan', 0);
        cy.get('#connection_ports')
            .select('VIRTUAL');
        cy.get('#connection_baudrates')
            .select('AUTO');
        cy.get('#printer_connect')
            .should('contain', 'Connect')
            .click();

        cy.get('#connection .accordion-inner', {timeout: 10000})
            .should('not.be.visible');
        cy.get('#state .accordion-inner strong:first')
            .should('contain', 'Operational');

        cy.get('#connection_wrapper a.accordion-toggle')
            .click();
        cy.get('#printer_connect')
            .should('be.visible')
            .should('contain', 'Disconnect')
            .click();

        cy.get('#state .accordion-inner strong:first')
            .should('contain', 'Offline');
    });
});
