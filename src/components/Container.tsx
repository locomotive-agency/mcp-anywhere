import React, { HTMLAttributes, ReactNode } from 'react';

interface ContainerProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
  className?: string;
}

export const Container: React.FC<ContainerProps> = ({ children, className = '', ...props }) => {
  return <div className={`container ${className}`} {...props}>{children}</div>;
};
