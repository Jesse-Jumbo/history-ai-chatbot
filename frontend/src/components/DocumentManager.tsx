import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './DocumentManager.css';

const API_BASE_URL = 'http://localhost:8000';

interface Document {
  id: number;
  title: string;
  category: string;
  source: string;
  created_at?: string;
  content?: string;
}

interface DocumentGroup {
  source: string;
  count: number;
  documents: Document[];
}

interface BotConfig {
  role_name: string;
  role_description?: string;
}

interface DocumentManagerProps {
  activeTab: 'chat' | 'documents';
  setActiveTab: (tab: 'chat' | 'documents') => void;
}

const DocumentManager: React.FC<DocumentManagerProps> = ({ activeTab, setActiveTab }) => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [documentGroups, setDocumentGroups] = useState<DocumentGroup[]>([]);
  const [showRoleConfig, setShowRoleConfig] = useState(false);
  const [botConfig, setBotConfig] = useState<BotConfig>({
    role_name: '成功大學歷史系的對話機器人',
    role_description: ''
  });
  const [isLoading, setIsLoading] = useState(false);
  const [deletingIds, setDeletingIds] = useState<Set<number>>(new Set());
  const [expandedSources, setExpandedSources] = useState<Set<string>>(new Set());
  const [selectedDocument, setSelectedDocument] = useState<Document | null>(null);

  useEffect(() => {
    loadDocuments();
    loadBotConfig();
  }, []);

  const loadBotConfig = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/bot-config`);
      setBotConfig(response.data);
    } catch (error) {
      console.error('載入機器人配置失敗:', error);
    }
  };

  const handleRoleConfigSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // 驗證數據上限
    if (botConfig.role_name.length > 50) {
      alert('角色名稱過長，最多 50 字符');
      return;
    }
    if (botConfig.role_description && botConfig.role_description.length > 500) {
      alert('角色描述過長，最多 500 字符');
      return;
    }
    
    if (!botConfig.role_name.trim()) {
      alert('請輸入角色名稱');
      return;
    }
    
    if (!confirm('確定要更新角色設定嗎？這將清空所有對話歷史。')) {
      return;
    }
    
    setIsLoading(true);
    try {
      const response = await axios.put(`${API_BASE_URL}/api/bot-config`, botConfig);
      alert(response.data.message || '角色設定已更新');
      setShowRoleConfig(false);
      
      // 清空對話歷史（通過 sessionStorage 事件通知 Chat 組件）
      sessionStorage.removeItem('chatHistory');
      window.dispatchEvent(new Event('clearChat'));
      
      await loadBotConfig();
    } catch (error: any) {
      console.error('更新角色設定失敗:', error);
      alert(error.response?.data?.detail || '更新角色設定失敗');
    } finally {
      setIsLoading(false);
    }
  };

  const loadDocuments = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/documents`);
      const docs = response.data;
      setDocuments(docs);
      
      // 按來源分組
      const groups: { [key: string]: Document[] } = {};
      docs.forEach((doc: Document) => {
        const source = doc.source || '未分類';
        if (!groups[source]) {
          groups[source] = [];
        }
        groups[source].push(doc);
      });
      
      const grouped: DocumentGroup[] = Object.entries(groups).map(([source, docs]) => ({
        source,
        count: docs.length,
        documents: docs
      }));
      
      setDocumentGroups(grouped);
      
      // 預設展開所有來源
      if (expandedSources.size === 0) {
        setExpandedSources(new Set(grouped.map(g => g.source)));
      }
    } catch (error) {
      console.error('載入文檔失敗:', error);
    }
  };



  const handleDeleteDocument = async (docId: number) => {
    if (!confirm('確定要刪除這筆資料嗎？')) return;
    
    setDeletingIds(prev => new Set(prev).add(docId));
    try {
      await axios.delete(`${API_BASE_URL}/api/documents/${docId}`);
      loadDocuments();
      alert('資料已刪除');
    } catch (error: any) {
      console.error('刪除失敗:', error);
      alert(`刪除失敗：${error.response?.data?.detail || error.message}`);
    } finally {
      setDeletingIds(prev => {
        const newSet = new Set(prev);
        newSet.delete(docId);
        return newSet;
      });
    }
  };

  const handleDeleteBySource = async (sourceId: string) => {
    if (!confirm(`確定要刪除來源「${sourceId}」的所有資料嗎？這將刪除 ${documentGroups.find(g => g.source === sourceId)?.count || 0} 筆資料。`)) return;
    
    try {
      const response = await axios.delete(`${API_BASE_URL}/api/documents/source/${encodeURIComponent(sourceId)}`);
      alert(response.data.message);
      loadDocuments();
    } catch (error: any) {
      console.error('刪除失敗:', error);
      alert(`刪除失敗：${error.response?.data?.detail || error.message}`);
    }
  };


  const toggleSource = (source: string) => {
    setExpandedSources(prev => {
      const newSet = new Set(prev);
      if (newSet.has(source)) {
        newSet.delete(source);
      } else {
        newSet.add(source);
      }
      return newSet;
    });
  };

  const handleDocumentClick = async (docId: number) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/documents/${docId}`);
      setSelectedDocument(response.data);
    } catch (error: any) {
      console.error('載入文檔內容失敗:', error);
      alert(`載入文檔內容失敗：${error.response?.data?.detail || error.message}`);
    }
  };

  return (
    <div className="document-manager">
      <div className="document-main">
        {/* 標籤按鈕和操作按鈕 - 放在頂部 */}
        <div className="tabs-container">
          <div className="tabs-left">
            <button
              className={`tab-button ${activeTab === 'chat' ? 'active' : ''}`}
              onClick={() => setActiveTab('chat')}
            >
              對話
            </button>
            <button
              className={`tab-button ${activeTab === 'documents' ? 'active' : ''}`}
              onClick={() => setActiveTab('documents')}
            >
              資料管理
            </button>
          </div>
          <div className="tabs-right">
            <button
              onClick={() => setShowRoleConfig(!showRoleConfig)}
              className="role-config-button"
              style={{
                padding: '8px 16px',
                background: '#4caf50',
                color: 'white',
                border: 'none',
                borderRadius: '8px',
                cursor: 'pointer',
                fontSize: '0.9rem',
                whiteSpace: 'nowrap',
                width: 'auto',
                minWidth: 'fit-content'
              }}
            >
              {showRoleConfig ? '取消設定' : '⚙️ 角色設定'}
            </button>
          </div>
        </div>

        {showRoleConfig && (
          <form onSubmit={handleRoleConfigSubmit} className="document-form" style={{ marginBottom: '20px', background: '#f9f9f9', padding: '20px', borderRadius: '8px' }}>
          <h3 style={{ marginTop: 0 }}>🤖 機器人角色設定</h3>
          <div className="form-group">
            <label>角色名稱 * (最多 50 字符)</label>
            <input
              type="text"
              value={botConfig.role_name}
              onChange={(e) => setBotConfig({ ...botConfig, role_name: e.target.value })}
              required
              maxLength={50}
              placeholder="例如：吳新榮、鄭成功、歷史系 AI 助手"
              style={{ width: '100%', padding: '8px', fontSize: '0.9rem' }}
            />
            <small style={{ color: '#666' }}>
              {botConfig.role_name.length}/50 字符
            </small>
          </div>

          <div className="form-group">
            <label>角色描述 (最多 500 字符，可選)</label>
            <textarea
              value={botConfig.role_description || ''}
              onChange={(e) => setBotConfig({ ...botConfig, role_description: e.target.value })}
              rows={4}
              maxLength={500}
              placeholder="例如：基於吳新榮日記的 QA 機器人，請以第一人稱回答問題"
              style={{ width: '100%', padding: '8px', fontSize: '0.9rem' }}
            />
            <small style={{ color: '#666' }}>
              {(botConfig.role_description || '').length}/500 字符
            </small>
          </div>

          <div style={{ 
            background: '#fff3cd', 
            padding: '12px', 
            borderRadius: '6px', 
            marginBottom: '15px',
            border: '1px solid #ffc107'
          }}>
            <strong>⚠️ 注意：</strong>更新角色設定將會<strong>清空所有對話歷史</strong>，並重新應用新的 System Prompt。
          </div>

          <button 
            type="submit" 
            disabled={isLoading} 
            className="submit-button"
            style={{
              width: 'auto',
              minWidth: 'fit-content',
              whiteSpace: 'nowrap'
            }}
          >
            {isLoading ? '更新中...' : '更新角色設定'}
          </button>
          </form>
        )}

        <div className="documents-list">
        <h3>現有資料（共 {documents.length} 筆，{documentGroups.length} 個來源）</h3>
        {documents.length === 0 ? (
          <p className="empty-message">尚無資料，請新增歷史資料或上傳 CSV 文件</p>
        ) : (
          <div className="documents-by-source">
            {documentGroups.map((group) => {
              const isExpanded = expandedSources.has(group.source);
              return (
                <div key={group.source} className="source-group">
                  <div className="source-header">
                    <div className="source-title-wrapper">
                      <button
                        onClick={() => toggleSource(group.source)}
                        className="expand-button"
                        title={isExpanded ? '收起' : '展開'}
                      >
                        {isExpanded ? '▼' : '▶'}
                      </button>
                      <h4>
                        📚 {group.source} 
                        <span className="count-badge">({group.count} 筆)</span>
                      </h4>
                    </div>
                    <div className="source-actions">
                      <button
                        onClick={() => handleDeleteBySource(group.source)}
                        className="delete-source-button"
                        title="刪除此來源的所有資料"
                      >
                        🗑️ 刪除來源
                      </button>
                    </div>
                  </div>
                  {isExpanded && (
                    <div className="documents-grid">
                      {group.documents.map((doc) => (
                        <div 
                          key={doc.id} 
                          className="document-card"
                          onClick={() => handleDocumentClick(doc.id)}
                          style={{ cursor: 'pointer' }}
                        >
                          <div className="document-header-row">
                            <h5>{doc.title || doc.source}</h5>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleDeleteDocument(doc.id);
                              }}
                              disabled={deletingIds.has(doc.id)}
                              className="delete-doc-button"
                              title="刪除此筆資料"
                            >
                              {deletingIds.has(doc.id) ? '刪除中...' : '✕'}
                            </button>
                          </div>
                          <div className="document-meta">
                            <span className="category">{doc.category}</span>
                          </div>
                          {doc.created_at && (
                            <div className="document-date">
                              {new Date(doc.created_at).toLocaleDateString('zh-TW')}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
        </div>

        {selectedDocument && (
        <div className="document-modal-overlay" onClick={() => setSelectedDocument(null)}>
          <div className="document-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-title-wrapper">
                <h3>{selectedDocument.title || selectedDocument.source}</h3>
                {selectedDocument.source && (
                  <span className="modal-source-badge">{selectedDocument.source}</span>
                )}
              </div>
              <button 
                className="modal-close-button"
                onClick={() => setSelectedDocument(null)}
              >
                ✕
              </button>
            </div>
            <div className="modal-content">
              <div className="modal-meta">
                <span className="category">{selectedDocument.category}</span>
                {selectedDocument.created_at && (
                  <span className="modal-date">
                    {new Date(selectedDocument.created_at).toLocaleDateString('zh-TW')}
                  </span>
                )}
              </div>
              <div className="modal-text">
                {selectedDocument.content || '無內容'}
              </div>
            </div>
          </div>
        </div>
        )}
      </div>
    </div>
  );
};

export default DocumentManager;

