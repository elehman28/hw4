import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
// The site's only two typefaces, self-hosted: a serif for display, a sans for everything else.
import '@fontsource-variable/playfair-display'
import '@fontsource-variable/inter'
import './index.css'
import App from './App.tsx'
import { AuthProvider } from './auth.tsx'
import { SearchResultsProvider } from './searchResults.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <SearchResultsProvider>
          <App />
        </SearchResultsProvider>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
)
