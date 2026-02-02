import React, { HTMLAttributes, ReactNode } from 'react';

interface SectionProps extends HTMLAttributes<HTMLElement> {
  children: ReactNode;
  className?: string;
  id?: string;
}

export const Section: React.FC<SectionProps> = ({ children, className = '', id, ...props }) => {
  return (
    <section id={id} className={`section ${className}`} {...props}>
      {children}
    </section>
  );
};
