import React, { useState } from 'react';
import './App.css';
import Chat from './components/Chat';
import DocumentManager from './components/DocumentManager';

function App() {
  const [activeTab, setActiveTab] = useState<'chat' | 'documents'>('chat');

  return (
    <div className="App">
      <header className="App-header">
        <h1>歷史系 AI 對話機器人</h1>
        <div className="tabs">
          <button
            className={activeTab === 'chat' ? 'active' : ''}
            onClick={() => setActiveTab('chat')}
          >
            對話
          </button>
          <button
            className={activeTab === 'documents' ? 'active' : ''}
            onClick={() => setActiveTab('documents')}
          >
            資料管理
          </button>
        </div>
      </header>
      <div className="tab-content" style={{ display: activeTab === 'chat' ? 'flex' : 'none', flex: 1, overflow: 'hidden', minHeight: 0 }}>
        <Chat />
      </div>
      <div className="tab-content" style={{ display: activeTab === 'documents' ? 'block' : 'none', flex: 1, overflow: 'hidden' }}>
        <DocumentManager />
      </div>
    </div>
  );
}

export default App;

