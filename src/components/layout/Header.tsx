import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Shield, Bell, HelpCircle, Search } from 'lucide-react';
import { useScan } from '../../hooks/useScan';

export const Header: React.FC = () => {
  const location = useLocation();
  const { showToast } = useScan();

  const navClass = (path: string) =>
    `nav-link ${location.pathname === path ? 'nav-link-active' : ''}`;

  return (
    <header className="w-full sticky top-0 z-50 bg-surface/90 backdrop-blur-xl border-b border-outline-variant/20 flex justify-between items-center px-6 py-3 gap-4">
      <Link to="/" className="flex items-center gap-3 shrink-0">
        <Shield className="w-6 h-6 text-primary" />
        <span className="font-headline text-base md:text-lg font-bold text-on-surface tracking-tight">
          AI Privacy Risk Simulator
        </span>
        <span className="bg-primary-container/60 text-primary px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-widest border border-primary/20 hidden sm:inline-block">
          v2.4
        </span>
      </Link>

      <nav className="hidden md:flex gap-6 items-center">
        <Link to="/" className={navClass('/')}>Overview</Link>
        <Link to="/upload" className={navClass('/upload')}>Analyze</Link>
        <Link to="/scanning" className={navClass('/scanning')}>
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-primary animate-pulse inline-block" />
            Live Scan
          </span>
        </Link>
        <Link to="/results" className={navClass('/results')}>Results</Link>
        <Link to="/history" className={navClass('/history')}>History</Link>
        <Link to="/settings" className={navClass('/settings')}>Settings</Link>
      </nav>

      <div className="flex items-center gap-3">
        <div className="relative hidden sm:block">
          <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-outline" />
          <input
            type="text"
            placeholder="Search scans..."
            className="bg-surface-container-low border border-outline-variant/30 text-on-surface text-xs pl-8 pr-3 py-1.5 rounded-lg focus:outline-none focus:border-primary w-36 md:w-44 transition-all"
          />
        </div>
        <button onClick={() => showToast('Notifications active.')} className="text-on-surface-variant hover:text-primary transition-colors p-1" title="Notifications">
          <Bell className="w-5 h-5" />
        </button>
        <button onClick={() => showToast('Help loaded.')} className="text-on-surface-variant hover:text-primary transition-colors p-1" title="Help">
          <HelpCircle className="w-5 h-5" />
        </button>
        <Link to="/settings" className="w-8 h-8 rounded-full border border-outline-variant/30 bg-secondary-container flex items-center justify-center overflow-hidden" title="Profile">
          <img className="w-full h-full object-cover" alt="Profile" src="https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=120&q=80" />
        </Link>
      </div>
    </header>
  );
};

export default Header;
