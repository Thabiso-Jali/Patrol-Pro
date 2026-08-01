import React from 'react';

export default function CustomersPage({
  customers,
  customerForm,
  setCustomerForm,
  showCreate,
  setShowCreate,
  showEdit,
  closeEdit,
  showArchive,
  closeArchive,
  loadCustomers,
  createCustomer,
  updateCustomer,
  startEdit,
  requestArchive,
  confirmArchive,
  ui,
  design,
}) {
  const { Button, Card, EnterpriseTable, Modal, TextField } = ui;
  const { colors, spacing, typography } = design;

  return (
    <div>
      <div style={{ marginBottom: spacing.lg }}>
        <div
          className="pp-page-heading-row"
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: spacing.md,
          }}
        >
          <h1 style={{ ...typography.headingXL, margin: 0, color: colors.slate900 }}>
            Customers
          </h1>
          <div className="pp-page-actions" style={{ display: 'flex', gap: spacing.md }}>
            <Button variant="secondary" icon="load" onClick={loadCustomers}>
              Refresh Customers
            </Button>
            <Button icon="add" onClick={() => setShowCreate(true)}>Add Customer</Button>
          </div>
        </div>
        <p style={{ ...typography.bodyLg, margin: 0, color: colors.slate500 }}>
          Manage customer contact and address records. Site operations and documents are not included.
        </p>
      </div>

      <Card header="Customer Register">
        <EnterpriseTable
          columns={[
            { key: 'name', label: 'Customer' },
            { key: 'email', label: 'Email' },
            { key: 'phone', label: 'Phone' },
            { key: 'address', label: 'Address' },
          ]}
          rows={customers.map((customer) => ({
            cells: {
              name: customer.name,
              email: customer.contact_email || 'Not set',
              phone: customer.phone || 'Not set',
              address: customer.address || 'Not set',
            },
            id: customer.id,
            raw: customer,
          }))}
          actions={(row) => (
            <>
              <Button
                size="sm"
                variant="secondary"
                icon="edit"
                onClick={() => startEdit(row.raw)}
                aria-label={`Edit customer ${row.cells.name}`}
              >
                Edit
              </Button>
              <Button
                size="sm"
                variant="danger"
                icon="trash"
                onClick={() => requestArchive(row.id)}
                aria-label={`Archive customer ${row.cells.name}`}
              >
                Archive
              </Button>
            </>
          )}
        />
      </Card>

      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="Add Customer">
        <CustomerFields
          customerForm={customerForm}
          setCustomerForm={setCustomerForm}
          TextField={TextField}
        />
        <div className="pp-form-actions" style={{ display: 'flex', gap: spacing.md, marginTop: spacing.lg }}>
          <Button variant="secondary" fullWidth onClick={() => setShowCreate(false)}>Cancel</Button>
          <Button fullWidth onClick={createCustomer}>Create Customer</Button>
        </div>
      </Modal>

      <Modal open={showEdit} onClose={closeEdit} title="Edit Customer">
        <CustomerFields
          customerForm={customerForm}
          setCustomerForm={setCustomerForm}
          TextField={TextField}
        />
        <div className="pp-form-actions" style={{ display: 'flex', gap: spacing.md, marginTop: spacing.lg }}>
          <Button variant="secondary" fullWidth onClick={closeEdit}>Cancel</Button>
          <Button fullWidth onClick={updateCustomer}>Save Customer</Button>
        </div>
      </Modal>

      <Modal open={showArchive} onClose={closeArchive} title="Archive Customer">
        <p style={{ ...typography.bodyMd, color: colors.slate700, marginBottom: spacing.lg }}>
          Archive this customer record? It will no longer appear in the active customer register.
        </p>
        <div className="pp-form-actions" style={{ display: 'flex', gap: spacing.md }}>
          <Button variant="secondary" fullWidth onClick={closeArchive}>Cancel</Button>
          <Button variant="danger" fullWidth onClick={confirmArchive}>Archive Customer</Button>
        </div>
      </Modal>
    </div>
  );
}

function CustomerFields({ customerForm, setCustomerForm, TextField }) {
  return (
    <>
      <TextField
        label="Customer Name"
        value={customerForm.name}
        onChange={(name) => setCustomerForm({ ...customerForm, name })}
        placeholder="Example Security Client"
        autoFocus
      />
      <TextField
        label="Contact Email"
        value={customerForm.contact_email}
        onChange={(contact_email) => setCustomerForm({ ...customerForm, contact_email })}
        placeholder="operations@example.com"
      />
      <TextField
        label="Phone"
        value={customerForm.phone}
        onChange={(phone) => setCustomerForm({ ...customerForm, phone })}
        placeholder="Contact telephone"
      />
      <TextField
        label="Address"
        value={customerForm.address}
        onChange={(address) => setCustomerForm({ ...customerForm, address })}
        placeholder="Customer correspondence address"
      />
    </>
  );
}
