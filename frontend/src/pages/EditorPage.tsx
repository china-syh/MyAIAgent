import React, { Suspense } from 'react';
import PageLoading from '../components/common/PageLoading';

const StoryEditor = React.lazy(() => import('../components/StoryEditor'));

const EditorPage: React.FC = () => (
  <Suspense fallback={<PageLoading />}>
    <StoryEditor />
  </Suspense>
);

export default EditorPage;