import React, { useState, useEffect } from 'react';
import { Container } from '../components/Container';
import { Button } from '../components/Button';
import { Menu, X, Github } from 'lucide-react';
import logo from '../assets/images/logo.png';
import { Link, useLocation, useNavigate } from 'react-router-dom';

export const Header: React.FC = () => {
  const [isScrolled, setIsScrolled] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 20);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const scrollToSection = (e: React.MouseEvent<HTMLAnchorElement>, id: string) => {
    e.preventDefault();
    if (location.pathname !== '/') {
      navigate('/', { state: { scrollTo: id } });
    } else {
      const element = document.getElementById(id);
      if (element) {
        element.scrollIntoView({ behavior: 'smooth' });
      }
    }
    setIsMobileMenuOpen(false);
  };

  // Handle scroll after navigation
  useEffect(() => {
    if (location.pathname === '/' && location.state && (location.state as any).scrollTo) {
      const id = (location.state as any).scrollTo;
      // Small timeout to ensure DOM is ready
      setTimeout(() => {
        const element = document.getElementById(id);
        if (element) {
          element.scrollIntoView({ behavior: 'smooth' });
        }
        // Clear state
        window.history.replaceState({}, document.title);
      }, 100);
    }
  }, [location]);

  const navLinks = [
    { label: 'Features', href: 'features', type: 'scroll' },
    { label: 'How it works', href: 'how-it-works', type: 'scroll' },
    { label: 'Security', href: 'security', type: 'scroll' },
    { label: 'Getting Started', href: '/getting-started', type: 'page' },
    { label: 'Deployment', href: '/deployment', type: 'page' },
  ];

  return (
    <header
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        isScrolled 
          ? 'bg-white-90 backdrop-blur-md border-b border-neutral-200 shadow-sm py-4' 
          : 'bg-transparent py-6'
      }`}
    >
      <Container>
        <div className="flex items-center justify-between">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-3 group">
            <img 
              src={logo} 
              alt="MCP Anywhere" 
              className="h-8 w-auto group-hover:scale-105 transition-transform"
            />
            <span className="font-bold text-xl text-neutral-900 tracking-tight">
              MCP Anywhere
            </span>
          </Link>

          {/* Desktop Nav */}
          <nav className="hidden md:flex items-center gap-8">
            {navLinks.map((item) => (
              item.type === 'scroll' ? (
                <a
                  key={item.label}
                  href={`#${item.href}`}
                  onClick={(e) => scrollToSection(e, item.href)}
                  className="text-sm font-medium text-neutral-600 hover:text-brand-600 transition-colors cursor-pointer"
                >
                  {item.label}
                </a>
              ) : (
                <Link
                  key={item.label}
                  to={item.href}
                  className={`text-sm font-medium transition-colors ${
                    location.pathname === item.href ? 'text-brand-600' : 'text-neutral-600 hover:text-brand-600'
                  }`}
                >
                  {item.label}
                </Link>
              )
            ))}
          </nav>
          
          <div className="hidden md:flex items-center gap-4">
             <a 
              href="https://github.com/locomotive-agency/mcp-anywhere" 
              target="_blank" 
              rel="noopener noreferrer"
              className="text-neutral-500 hover:text-brand-600 transition-colors"
            >
              <Github size={20} />
            </a>
            <Button size="sm" onClick={(e) => scrollToSection(e as any, 'get-started')}>Get Started</Button>
          </div>

           {/* Mobile Menu Toggle */}
           <button
            className="md:hidden p-2 text-neutral-900"
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            aria-label="Toggle menu"
          >
            {isMobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
          </button>
        </div>

        {/* Mobile Nav */}
        {isMobileMenuOpen && (
          <div className="md:hidden absolute top-full left-0 right-0 bg-white border-b border-neutral-200 shadow-lg p-4 animate-fade-in">
            <nav className="flex flex-col gap-4">
              {navLinks.map((item) => (
                item.type === 'scroll' ? (
                  <a
                    key={item.label}
                    href={`#${item.href}`}
                    className="text-lg font-medium text-neutral-900 py-2 border-b border-neutral-100"
                    onClick={(e) => scrollToSection(e, item.href)}
                  >
                    {item.label}
                  </a>
                ) : (
                  <Link
                    key={item.label}
                    to={item.href}
                    className="text-lg font-medium text-neutral-900 py-2 border-b border-neutral-100"
                    onClick={() => setIsMobileMenuOpen(false)}
                  >
                    {item.label}
                  </Link>
                )
              ))}
              <div className="flex flex-col gap-3 mt-4">
                 <Button 
                  variant="outline" 
                  href="https://github.com/locomotive-agency/mcp-anywhere"
                  target="_blank"
                >
                  <Github size={18} /> View on GitHub
                </Button>
                <Button onClick={(e) => scrollToSection(e as any, 'get-started')}>Get Started</Button>
              </div>
            </nav>
          </div>
        )}
      </Container>
    </header>
  );
};
