import React from 'react';
import { Hero } from '../sections/Hero';
import { SocialProof } from '../sections/SocialProof';
import { HowItWorks } from '../sections/HowItWorks';
import { Features } from '../sections/Features';
import { Security } from '../sections/Security';
import { Integrations } from '../sections/Integrations';
import { QuickStart } from '../sections/QuickStart';
import { FAQ } from '../sections/FAQ';
import { FinalCTA } from '../sections/FinalCTA';

export const LandingPage: React.FC = () => {
  return (
    <>
      <Hero />
      <SocialProof />
      <HowItWorks />
      <Features />
      <Security />
      <Integrations />
      <QuickStart />
      <FAQ />
      <FinalCTA />
    </>
  );
};
