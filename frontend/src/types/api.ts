export interface ApiSuccessResponse<T> {
  success: true;
  data: T;
  meta: {
    request_id: string;
    timestamp: string;
    page?: number;
    page_size?: number;
    total?: number;
    total_pages?: number;
  };
}

export interface ApiErrorResponse {
  success: false;
  error: {
    message: string;
    code: string;
    details?: unknown;
  };
  meta: {
    request_id: string;
    timestamp: string;
  };
}

export type ApiResponse<T> = ApiSuccessResponse<T> | ApiErrorResponse;

export interface User {
  id: number;
  email: string;
  is_active: boolean;
  created_at?: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface Repository {
  id: number;
  github_repo_id: number;
  name: string;
  full_name: string;
  url: string;
  default_branch: string;
  visibility: string;
  created_at: string;
  updated_at: string;
}

export interface RepositoryListItem {
  id: number;
  github_repo_id: number;
  name: string;
  full_name: string;
  url: string;
  default_branch: string;
  visibility: string;
  created_at: string;
  updated_at: string;
}

export interface Analysis {
  id: number;
  repository_id: number;
  status: "PENDING" | "RUNNING" | "COMPLETED" | "FAILED";
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
  summary: Record<string, unknown> | null;
  scores: Record<string, number> | null;
  findings: unknown[] | null;
  recommendations: string[] | null;
  error?: {
    code: string;
    message: string;
  };
}

export interface AnalysisHistoryItem {
  id: number;
  status: string;
  created_at: string;
  completed_at: string | null;
  score: number | null;
}

export interface PaginationMeta {
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}
