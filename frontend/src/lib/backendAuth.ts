export function getBackendAuthHeaders(): Record<string, string> {
  if (typeof window === "undefined") {
    return {};
  }

  const cookieMatch = document.cookie.match(/(?:^|; )session_token=([^;]*)/);
  const cookieToken = cookieMatch ? cookieMatch[1] : null;

  const tokenCandidates = [
    sessionStorage.getItem("agent_bi_access_token"),
    localStorage.getItem("agent_bi_access_token"),
    localStorage.getItem("access_token"),
    cookieToken,
  ];

  let accessToken = tokenCandidates.find((candidate) => !!candidate)?.trim() || "";
  let tenantSlug =
    sessionStorage.getItem("agent_bi_tenant_slug") ||
    localStorage.getItem("agent_bi_tenant_slug") ||
    "";

  // Se estiver usando Mock Auth ou rodando em Localhost sem token, usa os mocks
  const isLocalhost = typeof window !== "undefined" && (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1");
  const useMock = process.env.NEXT_PUBLIC_USE_MOCK_AUTH === "true" || process.env.NEXT_PUBLIC_USE_MOCK_AUTH === "True" || isLocalhost;
  
  if (useMock && !accessToken) {
    accessToken = "valid_mock_token";
    if (!tenantSlug) tenantSlug = "default";
  }

  const headers: Record<string, string> = {};
  if (accessToken) {
    // Para o Mock Auth, o backend aceita com ou sem o prefixo Bearer
    headers.Authorization = accessToken === "valid_mock_token" ? accessToken : `Bearer ${accessToken}`;
  }
  if (tenantSlug) {
    headers["X-Tenant-Slug"] = tenantSlug;
  }
  return headers;
}

export function getBackendJsonHeaders(): Record<string, string> {
  return {
    "Content-Type": "application/json",
    ...getBackendAuthHeaders(),
  };
}
