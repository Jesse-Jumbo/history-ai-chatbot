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
  embeddingStatus?: {
    total: number;
    with_embedding: number;
    without_embedding: number;
    percentage: number;
  };
}

const DocumentManager: React.FC = () => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [documentGroups, setDocumentGroups] = useState<DocumentGroup[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    title: '',
    content: '',
    category: '台灣史',
    source: ''
  });
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState('');
  const [deletingIds, setDeletingIds] = useState<Set<number>>(new Set());
  const [expandedSources, setExpandedSources] = useState<Set<string>>(new Set());
  const [selectedDocument, setSelectedDocument] = useState<Document | null>(null);
  const [generatingEmbeddings, setGeneratingEmbeddings] = useState<Set<string>>(new Set());
  const [embeddingProgress, setEmbeddingProgress] = useState<Map<string, any>>(new Map());

  useEffect(() => {
    loadDocuments();
  }, []);

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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    try {
      await axios.post(`${API_BASE_URL}/api/documents`, formData);
      setFormData({ title: '', content: '', category: '台灣史', source: '' });
      setShowForm(false);
      loadDocuments();
      alert('文檔已成功新增！');
    } catch (error) {
      console.error('新增文檔失敗:', error);
      alert('新增文檔失敗，請重試');
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.name.endsWith('.csv')) {
      alert('請上傳 CSV 文件');
      return;
    }

    setIsUploading(true);
    setUploadMessage('');
    
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post(`${API_BASE_URL}/api/documents/upload-csv`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      
      const msg = response.data.source
        ? `${response.data.message}（來源：${response.data.source}）`
        : response.data.message;
      
      // 先載入文檔列表
      await loadDocuments();
      
      // 檢查是否有未生成的 embedding
      const pendingEmbeddings = response.data.embeddings_pending || 0;
      if (pendingEmbeddings > 0) {
        setUploadMessage(`✅ ${msg}\n⏳ 有 ${pendingEmbeddings} 筆資料尚未生成向量嵌入，正在自動生成中...`);
        
        // 自動為該來源生成 embedding
        const sourceId = response.data.source;
        if (sourceId) {
          // 延遲一下，確保文檔列表已更新
          setTimeout(() => {
            generateEmbeddingsForSource(sourceId);
          }, 500);
        }
      } else {
        setUploadMessage(`✅ ${msg}\n✨ 所有資料已準備就緒，可以開始對話了！`);
      }
      // 清空文件輸入
      e.target.value = '';
    } catch (error: any) {
      console.error('上傳失敗:', error);
      setUploadMessage(`❌ 上傳失敗：${error.response?.data?.detail || error.message}`);
    } finally {
      setIsUploading(false);
    }
  };

  const generateEmbeddingsForSource = async (sourceId: string) => {
    if (generatingEmbeddings.has(sourceId)) {
      return; // 已在生成中
    }
    
    setGeneratingEmbeddings(prev => new Set(prev).add(sourceId));
    setUploadMessage(`⏳ 正在為「${sourceId}」生成向量嵌入...`);
    
    try {
      // 啟動生成任務
      const response = await axios.post(
        `${API_BASE_URL}/api/documents/generate-embeddings?source_id=${encodeURIComponent(sourceId)}`
      );
      
      const taskId = response.data.task_id;
      if (!taskId) {
        setUploadMessage(response.data.message || '所有文檔都已經有 embedding 了');
        setGeneratingEmbeddings(prev => {
          const newSet = new Set(prev);
          newSet.delete(sourceId);
          return newSet;
        });
        await loadDocuments();
        return;
      }
      
      // 輪詢進度
      const pollProgress = async () => {
        const maxAttempts = 600; // 最多輪詢 10 分鐘（每秒一次）
        let attempts = 0;
        
        const poll = async () => {
          try {
            const progressResponse = await axios.get(
              `${API_BASE_URL}/api/documents/embedding-progress/${taskId}`
            );
            
            const progress = progressResponse.data;
            setEmbeddingProgress(prev => {
              const newMap = new Map(prev);
              newMap.set(sourceId, progress);
              return newMap;
            });
            
            if (progress.status === 'completed') {
              // 完成
              setUploadMessage(
                `✅ 已成功為「${sourceId}」的 ${progress.total} 筆資料生成向量嵌入！\n✨ 現在可以開始對話了，搜索會更準確。`
              );
              setGeneratingEmbeddings(prev => {
                const newSet = new Set(prev);
                newSet.delete(sourceId);
                return newSet;
              });
              setEmbeddingProgress(prev => {
                const newMap = new Map(prev);
                newMap.delete(sourceId);
                return newMap;
              });
              await loadDocuments();
            } else if (progress.status === 'error') {
              // 錯誤
              setUploadMessage(
                `⚠️ 生成向量嵌入時發生錯誤：${progress.error}\n提示：您仍可使用關鍵字搜索功能。`
              );
              setGeneratingEmbeddings(prev => {
                const newSet = new Set(prev);
                newSet.delete(sourceId);
                return newSet;
              });
              setEmbeddingProgress(prev => {
                const newMap = new Map(prev);
                newMap.delete(sourceId);
                return newMap;
              });
            } else if (progress.status === 'processing') {
              // 繼續輪詢
              attempts++;
              if (attempts < maxAttempts) {
                setTimeout(poll, 1000); // 每秒輪詢一次
              } else {
                setUploadMessage('⚠️ 生成時間過長，請稍後手動檢查狀態');
                setGeneratingEmbeddings(prev => {
                  const newSet = new Set(prev);
                  newSet.delete(sourceId);
                  return newSet;
                });
              }
            }
          } catch (error: any) {
            if (error.response?.status === 404) {
              // 任務已完成並已清理
              setUploadMessage(`✅ 「${sourceId}」的向量嵌入生成已完成！`);
              setGeneratingEmbeddings(prev => {
                const newSet = new Set(prev);
                newSet.delete(sourceId);
                return newSet;
              });
              setEmbeddingProgress(prev => {
                const newMap = new Map(prev);
                newMap.delete(sourceId);
                return newMap;
              });
              await loadDocuments();
            } else {
              console.error('查詢進度失敗:', error);
              setTimeout(poll, 2000); // 錯誤時延長輪詢間隔
            }
          }
        };
        
        poll();
      };
      
      pollProgress();
      
    } catch (error: any) {
      console.error('生成 embedding 失敗:', error);
      setUploadMessage(`⚠️ 啟動生成任務失敗：${error.response?.data?.detail || error.message}\n提示：您仍可使用關鍵字搜索功能。`);
      setGeneratingEmbeddings(prev => {
        const newSet = new Set(prev);
        newSet.delete(sourceId);
        return newSet;
      });
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

  const handleDeleteAll = async () => {
    if (!confirm(`⚠️ 警告：確定要清空所有資料嗎？這將刪除所有 ${documents.length} 筆資料，此操作無法復原！`)) return;
    
    if (!confirm('請再次確認：真的要刪除所有資料嗎？')) return;
    
    try {
      const response = await axios.delete(`${API_BASE_URL}/api/documents/clear`);
      alert(response.data.message);
      loadDocuments();
      setExpandedSources(new Set());
    } catch (error: any) {
      console.error('清空失敗:', error);
      alert(`清空失敗：${error.response?.data?.detail || error.message}`);
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
      <div className="document-header">
        <h2>歷史資料管理</h2>
        <div className="header-actions">
          <label className="upload-button">
            {isUploading ? '上傳中...' : '📁 上傳 CSV'}
            <input
              type="file"
              accept=".csv"
              onChange={handleFileUpload}
              disabled={isUploading}
              style={{ display: 'none' }}
            />
          </label>
          <button onClick={() => setShowForm(!showForm)} className="add-button">
            {showForm ? '取消' : '+ 新增資料'}
          </button>
          {documents.length > 0 && (
            <button onClick={handleDeleteAll} className="delete-all-button" title="清空所有資料">
              🗑️ 清空所有資料
            </button>
          )}
        </div>
      </div>

      {uploadMessage && (
        <div className={`upload-message ${uploadMessage.startsWith('✅') ? 'success' : uploadMessage.startsWith('⏳') ? 'info' : 'error'}`} style={{ whiteSpace: 'pre-line' }}>
          {uploadMessage}
        </div>
      )}

      {showForm && (
        <form onSubmit={handleSubmit} className="document-form">
          <div className="form-group">
            <label>標題 *</label>
            <input
              type="text"
              value={formData.title}
              onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              required
              placeholder="例如：台灣史概述"
            />
          </div>

          <div className="form-group">
            <label>內容 *</label>
            <textarea
              value={formData.content}
              onChange={(e) => setFormData({ ...formData, content: e.target.value })}
              required
              rows={8}
              placeholder="輸入歷史資料內容..."
            />
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>分類</label>
              <select
                value={formData.category}
                onChange={(e) => setFormData({ ...formData, category: e.target.value })}
              >
                <option value="台灣史">台灣史</option>
                <option value="中國史">中國史</option>
                <option value="世界史">世界史</option>
                <option value="其他">其他</option>
              </select>
            </div>

            <div className="form-group">
              <label>來源</label>
              <input
                type="text"
                value={formData.source}
                onChange={(e) => setFormData({ ...formData, source: e.target.value })}
                placeholder="例如：歷史教科書"
              />
            </div>
          </div>

          <button type="submit" disabled={isLoading} className="submit-button">
            {isLoading ? '新增中...' : '新增資料'}
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
                        {group.embeddingStatus && group.embeddingStatus.without_embedding > 0 && (
                          <span className="embedding-warning" style={{ 
                            marginLeft: '10px', 
                            fontSize: '0.85rem', 
                            color: '#ff9800',
                            fontWeight: 'normal'
                          }}>
                            ⚠️ {group.embeddingStatus.without_embedding} 筆尚未生成向量嵌入
                          </span>
                        )}
                        {group.embeddingStatus && group.embeddingStatus.percentage === 100 && (
                          <span className="embedding-success" style={{ 
                            marginLeft: '10px', 
                            fontSize: '0.85rem', 
                            color: '#4caf50',
                            fontWeight: 'normal'
                          }}>
                            ✓ 已就緒
                          </span>
                        )}
                      </h4>
                    </div>
                    <div className="source-actions">
                      {group.embeddingStatus && group.embeddingStatus.without_embedding > 0 && (
                        <button
                          onClick={() => generateEmbeddingsForSource(group.source)}
                          disabled={generatingEmbeddings.has(group.source)}
                          className="generate-embedding-button"
                          title="為此來源生成向量嵌入以提升搜索準確度"
                          style={{
                            padding: '8px 16px',
                            background: '#ff9800',
                            color: 'white',
                            border: 'none',
                            borderRadius: '6px',
                            fontSize: '0.9rem',
                            cursor: generatingEmbeddings.has(group.source) ? 'not-allowed' : 'pointer',
                            opacity: generatingEmbeddings.has(group.source) ? 0.6 : 1
                          }}
                        >
                          {generatingEmbeddings.has(group.source) ? '生成中...' : '🔧 生成向量嵌入'}
                        </button>
                      )}
                      <button
                        onClick={() => handleDeleteBySource(group.source)}
                        className="delete-source-button"
                        title="刪除此來源的所有資料"
                      >
                        🗑️ 刪除來源
                      </button>
                    </div>
                  </div>
                  {generatingEmbeddings.has(group.source) && embeddingProgress.has(group.source) && (
                        <div style={{ 
                          background: '#f5f5f5', 
                          borderRadius: '8px', 
                          padding: '12px',
                          marginTop: '8px'
                        }}>
                          <div style={{ 
                            display: 'flex', 
                            justifyContent: 'space-between', 
                            marginBottom: '8px',
                            fontSize: '0.9rem',
                            color: '#666'
                          }}>
                            <span>生成中...</span>
                            <span>{embeddingProgress.get(group.source)?.percentage || 0}%</span>
                          </div>
                          <div style={{
                            width: '100%',
                            height: '8px',
                            background: '#e0e0e0',
                            borderRadius: '4px',
                            overflow: 'hidden'
                          }}>
                            <div style={{
                              width: `${embeddingProgress.get(group.source)?.percentage || 0}%`,
                              height: '100%',
                              background: 'linear-gradient(90deg, #4caf50 0%, #45a049 100%)',
                              transition: 'width 0.3s ease',
                              borderRadius: '4px'
                            }} />
                          </div>
                        </div>
                      )}
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
  );
};

export default DocumentManager;

