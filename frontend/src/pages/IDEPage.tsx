import React from 'react';
import { IDELayout } from '../components/ide/IDELayout';
import { ProblemProvider } from '../contexts/ProblemContext';

const IDEPage = () => {
  return (
    <ProblemProvider>
      <IDELayout />
    </ProblemProvider>
  );
};

export default IDEPage;
