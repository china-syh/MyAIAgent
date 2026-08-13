import React, { Suspense } from 'react';
import PageLoading from '../components/common/PageLoading';

const AgentMonitor = React.lazy(() => import('../components/AgentMonitor'));

const AgentPage: React.FC = () => (
  <Suspense fallback={<PageLoading />}>
    <AgentMonitor />
  </Suspense>
);

export default AgentPage;