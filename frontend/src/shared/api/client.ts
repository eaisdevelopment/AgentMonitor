import { apiVersion } from "../../generated/api";

export type FoundationShellState = Readonly<{
  applicationVersion: typeof apiVersion;
  message: string;
}>;

/**
 * The M1 contract intentionally publishes no business operations. This wrapper
 * is the only UI seam over generated output until P02 owns real API state.
 */
export function getFoundationShellState(): FoundationShellState {
  return {
    applicationVersion: apiVersion,
    message:
      "The local foundation is ready. Monitoring data will appear only after an approved provider integration is available.",
  };
}
