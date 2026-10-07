export function providerDisplayName(providerKey: string): string {
  if (providerKey === "claude") return "Claude";
  if (providerKey === "codex") return "Codex";
  return providerKey.replaceAll("_", " ");
}

export function providerConnectionCopy(providerKey: string) {
  const provider = providerDisplayName(providerKey);
  return Object.freeze({
    provider,
    connected: `${provider} connected`,
    setupRequired: `${provider} setup required`,
    differentAccount: `Different ${provider} account detected`,
    idle: `Confirm the email, then open ${provider}'s official sign-in in a separate browser window.`,
    requested: `Keep this page open. ${provider}'s official sign-in window is being opened.`,
    awaiting: `Complete sign-in in ${provider}'s browser window using the email below. This page will update after verification.`,
    verifying: `Sign-in finished. Checking that ${provider} reports the account you selected before enabling monitoring.`,
    wrongAccount: `${provider} reported a different identity from the selected email. Monitoring was not enabled by this attempt. Review the selected account before trying again.`,
    setupDescription: `${provider} sign-in succeeded, but its first-use setup still needs attention. Monitoring has not started. Check status after completing ${provider} setup.`,
    emailHelp: `Sign in with this email in ${provider}. Enter passwords and verification codes only on ${provider}'s official page.`,
    recoveryHelp: `Confirm the email used for the previously verified ${provider} account. The service will check it again before continuing.`,
  });
}
