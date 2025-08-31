export type User = {
  username: string;
  role: 'admin'|'manager';
  tenant_slug?: string|null;
  token: string;
};
