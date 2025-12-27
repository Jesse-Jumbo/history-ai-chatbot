import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import Mascot from './Mascot';
import Subtitle from './Subtitle';
import './Chat.css';

const API_BASE_URL = 'http://localhost:8000';

interface SourceDetail {
  source: string;
  doc_titles: string[];
}

interface Message {
  question: string;
  answer: string;
  timestamp: Date;
  sourceIds?: string[];
  source?: string;
  sourceDetails?: SourceDetail[]; // 來源詳細信息
  tempId?: number; // 臨時 ID，用於更新加載中的消息
}

const Chat: React.FC = () => {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<Message[]>(() => {
    // 從 sessionStorage 載入歷史對話（只在同一個瀏覽器會話中保持）
    // 每次重新開啟瀏覽器或重新載入頁面時，歷史記錄會重置
    const saved = sessionStorage.getItem('chatHistory');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        // 轉換 timestamp 字串回 Date 物件
        return parsed.map((msg: any) => ({
          ...msg,
          timestamp: new Date(msg.timestamp)
        }));
      } catch (e) {
        return [];
      }
    }
    return [];
  });
  const [isLoading, setIsLoading] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [currentSubtitle, setCurrentSubtitle] = useState('');
  const [synth, setSynth] = useState<SpeechSynthesis | null>(null);
  const [expandedSources, setExpandedSources] = useState<Set<number>>(new Set());
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // 檢查瀏覽器是否支援 Web Speech API
    if ('speechSynthesis' in window) {
      setSynth(window.speechSynthesis);
    }
  }, []);

  // 保存對話歷史到 sessionStorage（只在同一個瀏覽器會話中保持）
  // 切換頁面或重新載入時會保持，但關閉瀏覽器後會重置
  useEffect(() => {
    if (messages.length > 0) {
      sessionStorage.setItem('chatHistory', JSON.stringify(messages));
    } else {
      // 如果消息為空，清除 sessionStorage
      sessionStorage.removeItem('chatHistory');
    }
  }, [messages]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // 監聽清空對話事件（當角色設定更新時觸發）
  useEffect(() => {
    const handleClearChat = () => {
      setMessages([]);
      sessionStorage.removeItem('chatHistory');
    };
    
    window.addEventListener('clearChat', handleClearChat);
    return () => {
      window.removeEventListener('clearChat', handleClearChat);
    };
  }, []);

  const speakText = (text: string) => {
    if (!synth) {
      console.warn('瀏覽器不支援語音合成');
      return;
    }

    // 停止之前的語音
    synth.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'zh-TW';
    utterance.rate = 0.9;
    utterance.pitch = 1.1;
    utterance.volume = 1;

    utterance.onstart = () => {
      setIsSpeaking(true);
      setCurrentSubtitle(text);
    };

    utterance.onend = () => {
      setIsSpeaking(false);
      setCurrentSubtitle('');
    };

    utterance.onerror = () => {
      setIsSpeaking(false);
      setCurrentSubtitle('');
    };

    synth.speak(utterance);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const question = input.trim();
    setInput('');
    setIsLoading(true);

    // 立即顯示用戶的問題
    const tempMessageId = Date.now();
    setMessages(prev => [...prev, {
      question,
      answer: '', // 暫時為空，等待回答
      timestamp: new Date(),
      sourceIds: [],
      source: 'loading',
      tempId: tempMessageId
    }]);

    try {
      const response = await axios.post(`${API_BASE_URL}/api/ask`, {
        question: question,
        use_ai: true
      });

      const answer = response.data.answer;
      const sourceIds = response.data.source_ids;
      const source = response.data.source;
      const sourceDetails = response.data.source_details;
      
      // 更新剛才添加的消息
      setMessages(prev => prev.map(msg => 
        (msg as any).tempId === tempMessageId
          ? {
              question,
              answer,
              timestamp: new Date(),
              sourceIds: sourceIds || [],
              source: source,
              sourceDetails: sourceDetails || []
            }
          : msg
      ));

      // 播放語音
      speakText(answer);

    } catch (error) {
      console.error('Error:', error);
      const errorMsg = '抱歉，發生錯誤，請稍後再試。';
      // 更新錯誤消息
      setMessages(prev => prev.map(msg => 
        (msg as any).tempId === tempMessageId
          ? {
              question,
              answer: errorMsg,
              timestamp: new Date(),
              sourceIds: [],
              source: 'error'
            }
          : msg
      ));
      speakText(errorMsg);
    } finally {
      setIsLoading(false);
    }
  };

  const stopSpeaking = () => {
    if (synth) {
      synth.cancel();
      setIsSpeaking(false);
      setCurrentSubtitle('');
    }
  };

  const clearHistory = () => {
    if (confirm('確定要清除所有對話記錄嗎？')) {
      setMessages([]);
      setExpandedSources(new Set());
      sessionStorage.removeItem('chatHistory');
    }
  };

  const toggleSource = (messageIndex: number) => {
    setExpandedSources(prev => {
      const newSet = new Set(prev);
      if (newSet.has(messageIndex)) {
        newSet.delete(messageIndex);
      } else {
        newSet.add(messageIndex);
      }
      return newSet;
    });
  };

  return (
    <div className="chat-container">
      <div className="chat-main">
        <div className="chat-header-actions">
          {messages.length > 0 && (
            <button onClick={clearHistory} className="clear-history-button">
              🗑️ 清除記錄
            </button>
          )}
        </div>
        <Mascot isSpeaking={isSpeaking} text={currentSubtitle} />
        
        <div className="messages-container">
          {messages.length === 0 ? (
            <div className="welcome-message">
              <p>👋 歡迎使用歷史系 AI 對話機器人！</p>
              <p>請輸入您的問題，我會從資料庫中搜尋相關內容來回答您。</p>
            </div>
          ) : (
            messages.map((msg, idx) => (
              <div key={idx} className="message-group">
                <div className="message question">
                  <strong>你：</strong>{msg.question}
                </div>
                <div className="message answer">
                  <strong>小精靈：</strong>
                  {msg.answer ? (
                    <div className="answer-content">
                      <ReactMarkdown>{msg.answer}</ReactMarkdown>
                    </div>
                  ) : (
                    <span className="loading-text">正在思考...</span>
                  )}
                  {(msg.sourceDetails && msg.sourceDetails.length > 0) || (msg.sourceIds && msg.sourceIds.length > 0) ? (
                    <div className="source-info">
                      <button
                        className="source-toggle-button"
                        onClick={() => toggleSource(idx)}
                        type="button"
                      >
                        <span className="source-toggle-icon">
                          {expandedSources.has(idx) ? '▼' : '▶'}
                        </span>
                        <span className="source-toggle-text">
                          📚 來源
                          {msg.sourceDetails 
                            ? (() => {
                                const sourceCount = msg.sourceDetails.length;
                                const docCount = msg.sourceDetails.reduce((sum, detail) => 
                                  sum + (detail.doc_titles?.length || 0), 0
                                );
                                return `（${sourceCount} 個來源，${docCount} 筆資料）`;
                              })()
                            : `（${msg.sourceIds?.length || 0} 個來源）`}
                        </span>
                      </button>
                      {expandedSources.has(idx) && (
                        <div className="source-details">
                          {msg.sourceDetails && msg.sourceDetails.length > 0 ? (
                            msg.sourceDetails.map((detail, detailIdx) => (
                              <div key={detailIdx} className="source-detail-item">
                                <strong>{detail.source}</strong>
                                {detail.doc_titles && detail.doc_titles.length > 0 && (
                                  <span className="source-doc-titles">
                                    （{detail.doc_titles.length} 筆：{detail.doc_titles.join('、')}）
                                  </span>
                                )}
                              </div>
                            ))
                          ) : (
                            msg.sourceIds && msg.sourceIds.map((sourceId, sourceIdx) => (
                              <div key={sourceIdx} className="source-detail-item">
                                {sourceId}
                              </div>
                            ))
                          )}
                        </div>
                      )}
                    </div>
                  ) : null}
                </div>
              </div>
            ))
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="input-container">
          <form onSubmit={handleSubmit} className="input-form">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="輸入你的問題..."
              className="input-field"
              disabled={isLoading}
            />
            <button
              type="submit"
              disabled={isLoading || !input.trim()}
              className="submit-button"
            >
              發送
            </button>
            {isSpeaking && (
              <button
                type="button"
                onClick={stopSpeaking}
                className="stop-button"
              >
                停止
              </button>
            )}
          </form>
        </div>
      </div>

      <Subtitle text={currentSubtitle} isVisible={isSpeaking} />
    </div>
  );
};

export default Chat;

