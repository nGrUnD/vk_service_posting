import React from 'react';
import { createRoot } from 'react-dom/client';
import { ConfigProvider, message } from 'antd';

import App from './App.jsx';
import './index.css';

message.config({
  top: 24,
  duration: 3,
  maxCount: 3,
});

const container = document.getElementById('root');
const root = createRoot(container);

root.render(
  <React.StrictMode>
    <ConfigProvider
      theme={{
        token: {
          colorPrimary: '#4f46e5',
          borderRadius: 14,
          fontFamily: 'Inter, system-ui, sans-serif',
        },
      }}
      getPopupContainer={() => document.body}
    >
      <App />
    </ConfigProvider>
  </React.StrictMode>,
);
