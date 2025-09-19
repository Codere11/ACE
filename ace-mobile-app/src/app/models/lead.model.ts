export interface Lead {
  id: string;
  name: string;
  industry: string;
  score: number;
  stage: string;
  compatibility: boolean;
  interest: 'High' | 'Medium' | 'Low';
  phone: boolean;
  email: boolean;
  phoneText?: string;
  emailText?: string;
  lastMessage: string;
  lastSeenSec: number;
  notes: string;
}

export interface NotificationPayload {
  leadId: string;
  title: string;
  message: string;
  compatibility: number;
  interest: string;
  timestamp: number;
}

export interface User {
  username: string;
  role: 'admin' | 'manager';
  tenant_slug?: string;
}

export interface AuthResponse {
  token: string;
  user: User;
}