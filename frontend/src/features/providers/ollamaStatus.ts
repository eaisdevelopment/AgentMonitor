/** Present only normalized API states; provider content is never interpolated. */
export function ollamaStatusMessage(
  outcome: string,
  installedReason: string,
  loadedReason: string,
): string | null {
  if (outcome === "success") return null;
  if (outcome === "provider_unavailable" &&
      installedReason === "collection_in_progress" &&
      loadedReason === "collection_in_progress") {
    return "Another Ollama reading is in progress. Try again shortly.";
  }
  const messages: Readonly<Record<string, string>> = {
    partial: "Some Ollama information is unavailable.",
    provider_unavailable: "The local Ollama service is unavailable.",
    unverified_provider_version: "This Ollama version has not been verified for monitoring.",
    invalid_provider_data: "Ollama returned information that could not be verified.",
    deadline_exceeded: "The Ollama reading timed out.",
  };
  return messages[outcome] ?? "Local Ollama information is unavailable.";
}
