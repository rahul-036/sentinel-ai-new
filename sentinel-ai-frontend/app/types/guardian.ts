export interface GuardianCreate {
  name: string;
  phone: string;
  email?: string;
  relation: string;
  is_primary: boolean;
}

export interface GuardianUpdate {
  name?: string;
  phone?: string;
  email?: string;
  relation?: string;
  is_primary?: boolean;
}

export interface Guardian {
  id: string;
  name: string;
  phone: string;
  email?: string | null;
  relation: string;
  is_primary: boolean;
  created_at: string;
  updated_at: string;
}
