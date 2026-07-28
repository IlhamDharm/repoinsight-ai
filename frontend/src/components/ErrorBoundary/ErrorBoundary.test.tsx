import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import { ErrorBoundary } from "./ErrorBoundary";

function ThrowingComponent() {
  throw new Error("Test error");
}

describe("ErrorBoundary", () => {
  it("renders children when no error", () => {
    render(
      <ErrorBoundary>
        <div>Normal content</div>
      </ErrorBoundary>
    );
    expect(screen.getByText("Normal content")).toBeInTheDocument();
  });

  it("renders fallback UI when child throws", () => {
    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    render(
      <ErrorBoundary>
        <ThrowingComponent />
      </ErrorBoundary>
    );
    expect(screen.getByText(/Terjadi kesalahan/)).toBeInTheDocument();
    expect(screen.getByText("Test error")).toBeInTheDocument();
    consoleSpy.mockRestore();
  });
});
