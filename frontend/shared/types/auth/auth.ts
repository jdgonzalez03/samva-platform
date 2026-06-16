export interface LoginPayload {
  email: string;
  password: string;
}

export interface AuthTokens {
  refresh: string;
  access: string;
}

export interface AuthResponse {
  message: string;
  tokens: AuthTokens;
}

