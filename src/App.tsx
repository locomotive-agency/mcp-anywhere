import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom';
import { useEffect } from 'react';
import { Header } from './sections/Header';
import { Footer } from './sections/Footer';
import { LandingPage } from './pages/LandingPage';
import { GettingStarted } from './pages/GettingStarted';
import { Deployment } from './pages/Deployment';

const ScrollToTop = () => {
  const { pathname } = useLocation();

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);

  return null;
};

function App() {
  return (
    <BrowserRouter>
      <ScrollToTop />
      <div className="App">
        <Header />
        <main>
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/getting-started" element={<GettingStarted />} />
            <Route path="/deployment" element={<Deployment />} />
          </Routes>
        </main>
        <Footer />
      </div>
    </BrowserRouter>
  );
}

export default App;
