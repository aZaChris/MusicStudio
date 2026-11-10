import { QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'

import { createQueryClient } from './api/query-client'
import App from './App.tsx'
import { AuthProvider } from './auth/AuthProvider.tsx'
import './i18n'
import '@fontsource-variable/bricolage-grotesque/opsz.css'
import '@fontsource/figtree/400.css'
import '@fontsource/figtree/500.css'
import '@fontsource/figtree/600.css'
import '@fontsource/figtree/700.css'
import './theme/tokens.css'
import './theme/components.css'
import './theme/base.css'
import { ThemeProvider } from './theme/ThemeProvider.tsx'

const queryClient = createQueryClient()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <BrowserRouter>
          <AuthProvider>
            <App />
          </AuthProvider>
        </BrowserRouter>
      </ThemeProvider>
    </QueryClientProvider>
  </StrictMode>,
)
