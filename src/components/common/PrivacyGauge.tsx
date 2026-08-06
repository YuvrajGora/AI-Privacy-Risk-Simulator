import React from 'react';

interface PrivacyGaugeProps {
  score: number;
}

export const PrivacyGauge: React.FC<PrivacyGaugeProps> = ({ score }) => {
  const circumference = 282.7; // 2 * pi * 45
  const offset = circumference * (1 - Math.min(100, Math.max(0, score)) / 100);

  return (
    <div className="relative w-48 h-48 flex items-center justify-center">
      <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
        <circle
          className="text-surface-container-highest"
          cx="50"
          cy="50"
          r="45"
          fill="transparent"
          stroke="currentColor"
          strokeWidth="4"
        />
        <circle
          className="text-tertiary transition-all duration-1000 ease-out"
          cx="50"
          cy="50"
          r="45"
          fill="transparent"
          stroke="currentColor"
          strokeWidth="6"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="font-headline text-4xl font-bold text-on-surface">{score}</span>
        <span className="text-xs text-on-surface-variant">/ 100</span>
      </div>
    </div>
  );
};

export default PrivacyGauge;
