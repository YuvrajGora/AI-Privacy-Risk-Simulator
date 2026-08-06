import React from 'react';
import { useLocation } from 'react-router-dom';
import Header from './Header';
import Sidebar from './Sidebar';
import Footer from './Footer';
import { useScan } from '../../hooks/useScan';
import { Info } from 'lucide-react';

export const AppLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const location = useLocation();
  const { toast } = useScan();

  const isLanding = location.pathname === '/';

  return (
    <div className="min-h-screen flex flex-col bg-background text-on-surface antialiased">
      <Header />

      {/* Global Toast Banner */}
      {toast && (
        <div className="fixed top-16 right-6 z-50 animate-bounce">
          <div className="bg-surface-container-high border border-primary/40 text-on-surface text-xs px-4 py-3 rounded-lg shadow-2xl flex items-center gap-3 backdrop-blur-md">
            <Info className="w-4 h-4 text-primary" />
            <span>{toast.message}</span>
          </div>
        </div>
      )}

      <div className="flex-1 flex flex-col md:flex-row relative">
        {!isLanding && <Sidebar />}

        <main className="flex-1 min-w-0 bg-background overflow-y-auto">
          {children}
        </main>
      </div>

      <Footer />
    </div>
  );
};

export default AppLayout;
