import React from 'react';
import { Spin } from 'antd';

const PageLoading: React.FC = () => (
  <Spin
    size="large"
    style={{
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      minHeight: 300,
    }}
  />
);

export default PageLoading;