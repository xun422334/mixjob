import HomePage from './pages/HomePage'
import ErrorBoundary from './components/ErrorBoundary'

function App() {
  return (
    <ErrorBoundary>
      <HomePage />
    </ErrorBoundary>
  )
}

export default App
