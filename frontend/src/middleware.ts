import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
    const token = request.cookies.get('access_token')?.value;
    const { pathname } = request.nextUrl;

    // Public routes
    const publicRoutes = ['/login', '/register'];
    const isPublicRoute = publicRoutes.includes(pathname);

    // If trying to access protected route without token, redirect to login
    if (!isPublicRoute && !token && pathname !== '/') {
        // Check localStorage on client side instead
        return NextResponse.next();
    }

    // If logged in and trying to access login/register, redirect to dashboard
    if (isPublicRoute && token) {
        return NextResponse.redirect(new URL('/dashboard', request.url));
    }

    return NextResponse.next();
}

export const config = {
    matcher: ['/((?!api|_next/static|_next/image|favicon.ico).*)'],
};
