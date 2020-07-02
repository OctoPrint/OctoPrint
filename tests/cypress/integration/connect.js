describe('Connection test against virtual printer', () => {
    const username = 'admin';
    const password = 'test';

    beforeEach(() => {
        cy.request({
            method: 'POST',
            url: '/api/login',
            body: {
                "user": username,
                "pass": password
            }
        });

        cy.visit('/');

        cy.get('#navbar', {timeout: 10000})
            .should('be.visible');
    });

    it('connects', () => {
        cy.get('#state .accordion-inner strong:first')
            .should('contain', 'Offline');

        cy.get('#connection_ports')
            .select('VIRTUAL');
        cy.get('#printer_connect')
            .click();

        cy.get('#state .accordion-inner strong:first')
            .should('contain', 'Operational');
    });

    it('disconnects', () => {
        cy.get('#state .accordion-inner strong:first')
            .should('contain', 'Operational');

        cy.get('#connection_wrapper a.accordion-toggle')
            .click();
        cy.get('#printer_connect')
            .click();

        cy.get('#state .accordion-inner strong:first')
            .should('contain', 'Offline');
    });
});
