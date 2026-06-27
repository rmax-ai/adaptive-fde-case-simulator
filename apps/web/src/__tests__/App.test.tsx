import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import App from "../App";

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>,
  );
}

describe("App", () => {
  it("renders the launcher form without crashing", () => {
    renderWithProviders(<App />);
    expect(screen.getByText("AFCS")).toBeInTheDocument();
    expect(
      screen.getByText("Adaptive Forward Deployed Engineer Case Simulator"),
    ).toBeInTheDocument();
    expect(screen.getByText("Start Simulation")).toBeInTheDocument();
  });
});
