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

export type AnalysisStatus = "PENDING" | "RUNNING" | "COMPLETED" | "FAILED";

export interface Analysis {
  id: number;
  repository_id: number;
  status: AnalysisStatus;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
  summary: Record<string, unknown> | null;
  scores: Record<string, number> | null;
  findings: Finding[] | null;
  recommendations: string[] | null;
  error?: {
    code: string;
    message: string;
  };
}

export interface Finding {
  rule_id: string;
  severity: string;
  category: string;
  title: string;
  description: string;
  file_path: string | null;
  recommendation: string;
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

export interface AnalysisJobResponse {
  analysis_id: number;
  repository_id: number;
  status: string;
}

export interface ScanFile {
  path: string;
  language: string;
  size: number;
  lines: number;
}

export interface ScanResult {
  repository: string;
  branch: string;
  total_files: number;
  total_source_files: number;
  total_lines: number;
  languages: Record<string, number>;
  files: ScanFile[];
}

export interface DashboardStats {
  repository_count: number;
  analysis_count: number;
  recent_analyses: RecentAnalysisItem[];
}

export interface RecentAnalysisItem {
  id: number;
  status: string;
  created_at: string | null;
  completed_at: string | null;
  repository_id: number;
  repository_name: string;
  score: number | null;
}

export interface LanguageSummary {
  files: number;
  lines: number;
  percentage: number;
}

export interface AnalysisSummary {
  total_files: number;
  total_source_files: number;
  total_lines: number;
  dominant_language: string | null;
  languages: Record<string, LanguageSummary>;
}
