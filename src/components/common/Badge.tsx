import React from 'react';
import { RiskLevel } from '../../types';

interface BadgeProps {
  level: RiskLevel | string;
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({ level, className = '' }) => {
  const lvl = String(level).toUpperCase();
  if (lvl.includes('CRITICAL') || lvl.includes('HIGH')) {
    return (
      <span className={`bg-error-container text-on-error-container px-2.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${className}`}>
        {level}
      </span>
    );
  }
  if (lvl.includes('MEDIUM') || lvl.includes('ELEVATED')) {
    return (
      <span className={`bg-secondary-container text-on-secondary-container px-2.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${className}`}>
        {level}
      </span>
    );
  }
  return (
    <span className={`bg-primary-container text-on-primary-container px-2.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${className}`}>
      {level}
    </span>
  );
};

export default Badge;
