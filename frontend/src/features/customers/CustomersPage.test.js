import React from 'react';
import { renderToString } from 'react-dom/server';

import CustomersPage from './CustomersPage';

const ui = {
  Button: ({ children, ...props }) => <button {...props}>{children}</button>,
  Card: ({ header, children }) => <div><h2>{header}</h2>{children}</div>,
  EnterpriseTable: ({ rows }) => <div>{rows.map((row) => row.cells.name).join(', ')}</div>,
  Modal: ({ open, children }) => (open ? <div>{children}</div> : null),
  TextField: ({ label }) => <label>{label}<input /></label>,
};
const design = {
  colors: { slate900: '#0f172a', slate700: '#334155', slate500: '#64748b' },
  spacing: { md: 12, lg: 20 },
  typography: { headingXL: {}, bodyLg: {}, bodyMd: {} },
};

test('truthfully labels customer records and never calls them documents', () => {
  const html = renderToString(
    <CustomersPage
      customers={[]}
      customerForm={{ name: '', contact_email: '', phone: '', address: '' }}
      setCustomerForm={() => {}}
      showCreate={false}
      setShowCreate={() => {}}
      showEdit={false}
      closeEdit={() => {}}
      showArchive={false}
      closeArchive={() => {}}
      loadCustomers={() => {}}
      createCustomer={() => {}}
      updateCustomer={() => {}}
      startEdit={() => {}}
      requestArchive={() => {}}
      confirmArchive={() => {}}
      ui={ui}
      design={design}
    />
  );
  expect(html).toContain('Customers');
  expect(html).toContain('Customer Register');
  expect(html).not.toContain('Documents');
  expect(html).not.toContain('Site File');
});
