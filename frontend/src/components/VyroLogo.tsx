import React from 'react';

interface VyroLogoProps {
  size?: 'sm' | 'md' | 'lg';
  showTagline?: boolean;
}

export const VyroLogo: React.FC<VyroLogoProps> = ({ size = 'sm', showTagline = false }) => {
  const iconDim = size === 'lg' ? 'h-11 w-11' : size === 'md' ? 'h-8 w-8' : 'h-6 w-6';
  const wordSize =
    size === 'lg' ? 'text-[22px]' : size === 'md' ? 'text-[17px]' : 'text-[15px]';

  return (
    <span className="inline-flex items-center gap-2.5">
      <svg
        viewBox="0 0 64 64"
        fill="none"
        className={`${iconDim} shrink-0`}
        aria-hidden="true"
      >
        <rect
          width="64"
          height="64"
          rx="16"
          className="fill-[#1D1D1F] dark:fill-[#F5F5F7]"
        />
        <path
          d="M17 17L29.6 32L17 47H24.6L33.4 36.2L42.2 47H49.8L37.2 32L49.8 17H42.2L33.4 27.8L24.6 17H17Z"
          className="fill-white dark:fill-[#0B0B0C]"
        />
        <circle cx="48.5" cy="17" r="3.6" className="fill-[#0071E3] dark:fill-[#2997FF]" />
      </svg>
      <span className="flex flex-col leading-none">
        <span className={`${wordSize} font-semibold tracking-[0.06em] text-apple-ink`}>
          VYRO<span className="text-apple-blue">-X</span>
        </span>
        {showTagline && (
          <span className="mt-1 text-[11px] font-normal tracking-normal text-apple-secondary">
            Human Intelligence. Agent Evolution.
          </span>
        )}
      </span>
    </span>
  );
};
