import React from 'react';

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'brand' | 'neutral' | 'success' | 'warning' | 'danger';
}

export const Badge: React.FC<BadgeProps> = ({ children, variant = 'brand' }) => {
  return <span className={`badge badge-${variant}`}>{children}</span>;
};
