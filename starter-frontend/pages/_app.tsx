import type { AppProps } from 'next/app';
import { Provider } from 'react-redux';
import { useEffect } from 'react';
import { store } from '@/lib/store';
import { hydrateAuth } from '@/lib/slices/authSlice';
import '@/styles/globals.css';

function AuthHydration({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    // Hydrate auth state from localStorage on client-side
    store.dispatch(hydrateAuth());
  }, []);

  return <>{children}</>;
}

export default function App({ Component, pageProps }: AppProps) {
  return (
    <Provider store={store}>
      <AuthHydration>
        <Component {...pageProps} />
      </AuthHydration>
    </Provider>
  );
}
