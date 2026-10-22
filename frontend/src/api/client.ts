import { ApiError } from "../utils/errors";
import type { ApiSuccessResponse, ApiResponse } from "../types/api";

const BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "";

function getToken(): string | null {
  return localStorage.getItem("repoinsight_token");
}

export function setToken(token: string): void {
  localStorage.setItem("repoinsight_token", token);
}

export function removeToken(): void {
  localStorage.removeItem("repoinsight_token");
}

interface RequestOptions extends Omit<RequestInit, "method" | "body"> {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
}

export async function apiRequest<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const { method = "GET", body, headers: extraHeaders, ...rest } = options;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(extraHeaders as Record<string, string>),
  };

  const token = getToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${BASE_URL}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
    ...rest,
  });

  const json: ApiResponse<T> = await response.json();

  if (!response.ok || !json.success) {
    const errorBody = json.success
      ? { message: "Terjadi kesalahan", code: "unknown_error" }
      : json.error;
    throw new ApiError(response.status, errorBody);
  }

  return json.data;
}

export async function apiRequestFull<T>(
  path: string,
  options: RequestOptions = {},
): Promise<ApiSuccessResponse<T>> {
  const { method = "GET", body, headers: extraHeaders, ...rest } = options;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(extraHeaders as Record<string, string>),
  };

  const token = getToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${BASE_URL}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
    ...rest,
  });

  const json: ApiResponse<T> = await response.json();

  if (!response.ok || !json.success) {
    const errorBody = json.success
      ? { message: "Terjadi kesalahan", code: "unknown_error" }
      : json.error;
    throw new ApiError(response.status, errorBody);
  }

  return json;
}

export const api = {
  get: <T>(path: string, options?: RequestOptions) =>
    apiRequest<T>(path, { ...options, method: "GET" }),

  post: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    apiRequest<T>(path, { ...options, method: "POST", body }),

  put: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    apiRequest<T>(path, { ...options, method: "PUT", body }),

  patch: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    apiRequest<T>(path, { ...options, method: "PATCH", body }),

  delete: <T>(path: string, options?: RequestOptions) =>
    apiRequest<T>(path, { ...options, method: "DELETE" }),
};
