import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// Rotas que exigem autenticação
const protectedRoutes = ["/projects", "/dashboard"];

// Rotas exclusivas para usuários NÃO logados (Login, MFA, etc.)
const authRoutes = ["/login", "/login/mfa"];

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  
  // No Agent-BI, utilizamos o cookie 'session_token' ou similar do Cognito/Amplify
  // Simulação de verificação de token (em produção, validar via JWT)
  const isAuthenticated = request.cookies.get("session_token")?.value;

  // 1. Se tentar acessar rota protegida SEM estar logado -> Redirect Login
  if (protectedRoutes.some(route => pathname.startsWith(route)) && !isAuthenticated) {
    const loginUrl = new URL("/login", request.url);
    // Preservar a rota original para redirecionar de volta após o login
    loginUrl.searchParams.set("callbackUrl", pathname);
    return NextResponse.redirect(loginUrl);
  }

  // 2. Se já estiver logado e tentar ir para /login -> Redirect Projects
  if (authRoutes.some(route => pathname.startsWith(route)) && isAuthenticated) {
    return NextResponse.redirect(new URL("/projects", request.url));
  }

  return NextResponse.next();
}

// Configurar as rotas que o middleware deve observar
export const config = {
  matcher: [
    "/projects/:path*",
    "/dashboard/:path*",
    "/login/:path*",
  ],
};
