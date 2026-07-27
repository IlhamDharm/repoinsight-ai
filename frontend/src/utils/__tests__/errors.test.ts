import { describe, it, expect } from "vitest";
import { getErrorMessage, getErrorTitle } from "../errors";

describe("getErrorMessage", () => {
  it("returns message from ApiError", () => {
    const error = { statusCode: 401, code: "auth_error", message: "Unauthorized" };
    expect(getErrorMessage(error)).toBe("Terjadi kesalahan yang tidak diketahui.");
  });

  it("returns default message for unknown error", () => {
    expect(getErrorMessage(new Error("something"))).toBe("something");
  });

  it("returns default message for string", () => {
    expect(getErrorMessage("oops")).toBe("Terjadi kesalahan yang tidak diketahui.");
  });
});

describe("getErrorTitle", () => {
  it("returns title for 401", () => {
    expect(getErrorTitle(401)).toBe("Tidak Terautentikasi");
  });

  it("returns title for 404", () => {
    expect(getErrorTitle(404)).toBe("Tidak Ditemukan");
  });

  it("returns title for 500", () => {
    expect(getErrorTitle(500)).toBe("Kesalahan Server");
  });

  it("returns generic title for unknown code", () => {
    expect(getErrorTitle(418)).toBe("Kesalahan");
  });
});
