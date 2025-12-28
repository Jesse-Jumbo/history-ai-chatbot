import React, { useState } from 'react';
import './App.css';
import Chat from './components/Chat';
import DocumentManager from './components/DocumentManager';

function App() {
  const [activeTab, setActiveTab] = useState<'chat' | 'documents'>('chat');

  return (
    <div className="App">
      <header className="App-header">
        <h1 className="app-title">歷史系 AI 對話機器人</h1>
      </header>
      <div className="tab-content" style={{ display: activeTab === 'chat' ? 'flex' : 'none', flex: 1, overflow: 'hidden', minHeight: 0 }}>
        <Chat activeTab={activeTab} setActiveTab={setActiveTab} />
      </div>
      <div className="tab-content" style={{ display: activeTab === 'documents' ? 'flex' : 'none', flex: 1, overflow: 'hidden', minHeight: 0 }}>
        <DocumentManager activeTab={activeTab} setActiveTab={setActiveTab} />
      </div>
    </div>
  );
}

export default App;

