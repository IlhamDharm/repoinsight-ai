import type { ApiErrorResponse } from "../types/api";

export class ApiError extends Error {
  public readonly statusCode: number;
  public readonly code: string;
  public readonly details?: unknown;

  constructor(statusCode: number, errorBody: ApiErrorResponse["error"]) {
    super(errorBody.message);
    this.name = "ApiError";
    this.statusCode = statusCode;
    this.code = errorBody.code;
    this.details = errorBody.details;
  }
}

export function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error) {
    if (error.name === "TypeError" && error.message.includes("fetch")) {
      return "Tidak dapat terhubung ke server. Periksa koneksi internet Anda.";
    }
    return error.message;
  }
  return "Terjadi kesalahan yang tidak diketahui.";
}

export function getErrorTitle(statusCode: number): string {
  switch (statusCode) {
    case 401:
      return "Tidak Terautentikasi";
    case 403:
      return "Akses Ditolak";
    case 404:
      return "Tidak Ditemukan";
    case 422:
      return "Input Tidak Valid";
    case 429:
      return "Terlalu Banyak Request";
    case 500:
      return "Kesalahan Server";
    case 502:
      return "Layanan Tidak Tersedia";
    case 504:
      return "Server Timeout";
    default:
      return "Kesalahan";
  }
}
