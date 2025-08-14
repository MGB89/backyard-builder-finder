import NextAuth, { NextAuthOptions } from 'next-auth';
import GoogleProvider from 'next-auth/providers/google';
import AzureADProvider from 'next-auth/providers/azure-ad';
import { JWT } from 'next-auth/jwt';
import { Session } from 'next-auth';
import { randomBytes } from 'crypto';
import { SignJWT } from 'jose';

const authOptions: NextAuthOptions = {
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
      authorization: {
        params: {
          prompt: 'consent',
          access_type: 'offline',
          response_type: 'code',
          scope: 'openid email profile',
        },
      },
    }),
    AzureADProvider({
      clientId: process.env.AZURE_AD_CLIENT_ID!,
      clientSecret: process.env.AZURE_AD_CLIENT_SECRET!,
      tenantId: process.env.AZURE_AD_TENANT_ID || 'common',
      authorization: {
        params: {
          scope: 'openid email profile User.Read',
        },
      },
    }),
  ],
  
  callbacks: {
    async signIn({ user, account, profile }) {
      try {
        // Validate required fields
        if (!user.email) {
          console.error('Sign-in rejected: No email provided');
          return false;
        }
        
        // Call backend to handle user creation/update
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/auth/signin`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            email: user.email,
            name: user.name,
            image: user.image,
            provider: account?.provider,
            providerId: account?.providerAccountId,
          }),
        });
        
        if (!response.ok) {
          console.error('Backend sign-in failed:', response.statusText);
          return false;
        }
        
        const userData = await response.json();
        
        // Store user data in the user object for jwt callback
        user.id = userData.id;
        user.orgId = userData.org_id;
        user.role = userData.role;
        
        return true;
      } catch (error) {
        console.error('Sign-in error:', error);
        return false;
      }
    },
    
    async jwt({ token, user, account, profile, trigger }) {
      // Initial sign in
      if (account && user) {
        token.accessToken = account.access_token;
        token.refreshToken = account.refresh_token;
        token.provider = account.provider;
        token.userId = user.id;
        token.email = user.email;
        token.orgId = user.orgId;
        token.role = user.role;
        token.iat = Math.floor(Date.now() / 1000);
        token.exp = Math.floor(Date.now() / 1000) + (30 * 60); // 30 minutes
      }
      
      // Token refresh - check if token is about to expire
      if (trigger === 'update' || (token.exp && Date.now() / 1000 > token.exp - 300)) {
        try {
          // Refresh user data from backend
          const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/auth/refresh`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${token.accessToken}`,
            },
            body: JSON.stringify({ userId: token.userId }),
          });
          
          if (response.ok) {
            const refreshedUser = await response.json();
            token.orgId = refreshedUser.org_id;
            token.role = refreshedUser.role;
            token.exp = Math.floor(Date.now() / 1000) + (30 * 60);
          }
        } catch (error) {
          console.error('Token refresh error:', error);
        }
      }
      
      return token;
    },
    
    async session({ session, token }: { session: Session; token: JWT }) {
      // Send properties to the client
      if (session.user) {
        session.user.id = token.userId as string;
        session.user.email = token.email as string;
      }
      
      // Add custom properties
      session.accessToken = token.accessToken as string;
      session.orgId = token.orgId as string;
      session.role = token.role as string;
      
      return session;
    },
    
    async redirect({ url, baseUrl }) {
      // Allows relative callback URLs
      if (url.startsWith('/')) return `${baseUrl}${url}`;
      // Allows callback URLs on the same origin
      else if (new URL(url).origin === baseUrl) return url;
      return baseUrl;
    },
  },
  
  pages: {
    signIn: '/auth/signin',
    signOut: '/auth/signout',
    error: '/auth/error',
    verifyRequest: '/auth/verify-request',
  },
  
  session: {
    strategy: 'jwt',
    maxAge: 8 * 60 * 60, // 8 hours
    updateAge: 24 * 60 * 60, // Update session every 24 hours
  },
  
  jwt: {
    maxAge: 30 * 60, // 30 minutes
    encode: async ({ secret, token }) => {
      // Add additional security headers
      const encodedToken = await new SignJWT({
        ...token,
        iss: process.env.NEXTAUTH_URL,
        aud: process.env.NEXTAUTH_URL,
        nonce: randomBytes(16).toString('hex'),
      })
        .setProtectedHeader({ alg: 'HS256' })
        .setIssuedAt()
        .setExpirationTime('30m')
        .sign(new TextEncoder().encode(secret));
      
      return encodedToken;
    },
  },
  
  cookies: {
    sessionToken: {
      name: process.env.NODE_ENV === 'production' 
        ? '__Secure-next-auth.session-token' 
        : 'next-auth.session-token',
      options: {
        httpOnly: true,
        sameSite: 'lax',
        path: '/',
        secure: process.env.NODE_ENV === 'production',
        domain: process.env.NODE_ENV === 'production' 
          ? process.env.NEXTAUTH_URL?.replace(/https?:\/\//, '').split('/')[0]
          : undefined,
      },
    },
    callbackUrl: {
      name: process.env.NODE_ENV === 'production'
        ? '__Secure-next-auth.callback-url'
        : 'next-auth.callback-url',
      options: {
        sameSite: 'lax',
        path: '/',
        secure: process.env.NODE_ENV === 'production',
      },
    },
    csrfToken: {
      name: process.env.NODE_ENV === 'production'
        ? '__Host-next-auth.csrf-token'
        : 'next-auth.csrf-token',
      options: {
        httpOnly: true,
        sameSite: 'lax',
        path: '/',
        secure: process.env.NODE_ENV === 'production',
      },
    },
  },
  
  secret: process.env.NEXTAUTH_SECRET,
  
  debug: process.env.NODE_ENV === 'development',
};

const handler = NextAuth(authOptions);

export { handler as GET, handler as POST };