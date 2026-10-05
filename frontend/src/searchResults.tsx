import { createContext, useContext, useState } from 'react'
import type { ReactNode } from 'react'
import type { SearchResults } from './api'

// Holds the latest catalogue search from the chat agent so the Products page can show it.
// Saved in sessionStorage so results survive opening a product and coming back (or a reload).
const STORAGE_KEY = 'cc_search_results'

interface SearchResultsState {
  results: SearchResults | null
  showResults: (r: SearchResults) => void
  clearResults: () => void
}

const SearchResultsContext = createContext<SearchResultsState | null>(null)

function loadSaved(): SearchResults | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    return raw ? (JSON.parse(raw) as SearchResults) : null
  } catch {
    return null
  }
}

export function SearchResultsProvider({ children }: { children: ReactNode }) {
  const [results, setResults] = useState<SearchResults | null>(loadSaved)

  const value: SearchResultsState = {
    results,
    showResults: (r) => {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(r))
      setResults(r)
    },
    clearResults: () => {
      sessionStorage.removeItem(STORAGE_KEY)
      setResults(null)
    },
  }

  return <SearchResultsContext.Provider value={value}>{children}</SearchResultsContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useSearchResults() {
  const ctx = useContext(SearchResultsContext)
  if (!ctx) throw new Error('useSearchResults must be used inside SearchResultsProvider')
  return ctx
}
