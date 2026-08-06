import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ScanProvider } from './context/ScanContext';
import AppLayout from './components/layout/AppLayout';
import LandingPage from './pages/LandingPage';
import UploadPage from './pages/UploadPage';
import ScanningPage from './pages/ScanningPage';
import ResultsPage from './pages/ResultsPage';
import HistoryPage from './pages/HistoryPage';
import SettingsPage from './pages/SettingsPage';

export const App: React.FC = () => {
  return (
    <ScanProvider>
      <Router>
        <AppLayout>
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/upload" element={<UploadPage />} />
            <Route path="/scanning" element={<ScanningPage />} />
            <Route path="/results" element={<ResultsPage />} />
            <Route path="/results/:id" element={<ResultsPage />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </AppLayout>
      </Router>
    </ScanProvider>
  );
};

export default App;
