import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import './index.css'
import App from './App.tsx'
import { ErrorBoundary } from './components/errors/ErrorBoundary'
import { AuthProvider } from './contexts/AuthContext'
import { queryClient } from './lib/react-query'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ErrorBoundary
      onError={(error, errorInfo) => {
        // Log to error reporting service in production
        console.error('Application Error:', error, errorInfo);
        // TODO: Send to Sentry or other error tracking service
      }}
    >
      <BrowserRouter>
        <AuthProvider>
          <QueryClientProvider client={queryClient}>
            <App />
            {/* React Query Devtools (only shows in development) */}
            {import.meta.env.DEV && <ReactQueryDevtools initialIsOpen={false} />}
          </QueryClientProvider>
        </AuthProvider>
      </BrowserRouter>
    </ErrorBoundary>
  </StrictMode>,
)
