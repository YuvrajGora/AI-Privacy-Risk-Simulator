import React from 'react';
import { NavLink } from 'react-router-dom';
import { Home, UploadCloud, ScanLine, BarChart3, History, Settings } from 'lucide-react';

const links = [
  { to: '/',         icon: Home,        label: 'Overview' },
  { to: '/upload',   icon: UploadCloud, label: 'Analyze' },
  { to: '/scanning', icon: ScanLine,    label: 'Live Scan' },
  { to: '/results',  icon: BarChart3,   label: 'Results' },
  { to: '/history',  icon: History,     label: 'History' },
  { to: '/settings', icon: Settings,    label: 'Settings' },
];

export const Sidebar: React.FC = () => {
  return (
    <aside className="hidden lg:flex flex-col w-56 shrink-0 bg-surface-container-low border-r border-outline-variant/20 py-6 px-3 gap-1">
      {links.map(({ to, icon: Icon, label }) => (
        <NavLink
          key={to}
          to={to}
          end={to === '/'}
          className={({ isActive }) =>
            `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
              isActive
                ? 'bg-primary-container text-primary font-semibold'
                : 'text-on-surface-variant hover:bg-surface-container hover:text-on-surface'
            }`
          }
        >
          <Icon className="w-4 h-4 shrink-0" />
          {label}
        </NavLink>
      ))}
    </aside>
  );
};

export default Sidebar;
