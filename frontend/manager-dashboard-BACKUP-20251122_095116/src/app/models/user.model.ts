export interface User {
  id: number;
  username: string;
  email: string;
  role: 'org_admin' | 'org_user';
  organization_id: number;
  organization_slug?: string;
  is_active: boolean;
  created_at: string;
  last_login?: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  token: string;
  user: User;
}

export interface UserCreate {
  username: string;
  email: string;
  password: string;
  role: 'org_admin' | 'org_user';
  organization_id: number;
  is_active: boolean;
}

export interface UserUpdate {
  username?: string;
  email?: string;
  password?: string;
  role?: 'org_admin' | 'org_user';
  is_active?: boolean;
}
