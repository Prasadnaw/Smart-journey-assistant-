import { Routes, Route } from 'react-router-dom'
import SearchPage from './pages/SearchPage'
import TripDetailsPage from './pages/TripDetailsPage'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<SearchPage />} />
      <Route path="/trip/:id" element={<TripDetailsPage />} />
    </Routes>
  )
}
