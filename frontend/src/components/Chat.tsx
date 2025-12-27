import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import Mascot from './Mascot';
import Subtitle from './Subtitle';
import './Chat.css';

// 從環境變數獲取 API 地址，如果沒有則使用默認值
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

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
  
  // 拍照和變老相關狀態
  const [showCamera, setShowCamera] = useState(false);
  const [agedPhotoUrl, setAgedPhotoUrl] = useState<string | null>(null);
  const [isProcessingPhoto, setIsProcessingPhoto] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    // 檢查是否需要拍照（如果還沒有變老照片）
    const savedAgedPhoto = sessionStorage.getItem('agedPhotoUrl');
    if (savedAgedPhoto) {
      setAgedPhotoUrl(savedAgedPhoto);
    }
    // 注意：不自動啟動攝影機，讓用戶點擊按鈕啟動
  }, []);

  useEffect(() => {
    // 檢查瀏覽器是否支援 Web Speech API（作為備用）
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

  const speakText = async (text: string) => {
    // 停止之前的語音
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    if (synth) {
      synth.cancel();
    }

    try {
      // 優先使用 Google TTS
      const response = await axios.post(
        `${API_BASE_URL}/api/tts`,
        {
          text: text,
          lang: 'zh-TW',
          rate: 0.9,  // 老人聲音稍慢
          pitch: -2.0  // 老人聲音較低
        },
        {
          responseType: 'blob'
        }
      );

      // 創建音訊 URL 並播放
      const audioUrl = URL.createObjectURL(response.data);
      const audio = new Audio(audioUrl);
      audioRef.current = audio;

      audio.onplay = () => {
        setIsSpeaking(true);
        setCurrentSubtitle(text);
      };

      audio.onended = () => {
        setIsSpeaking(false);
        setCurrentSubtitle('');
        URL.revokeObjectURL(audioUrl);
        audioRef.current = null;
      };

      audio.onerror = () => {
        setIsSpeaking(false);
        setCurrentSubtitle('');
        URL.revokeObjectURL(audioUrl);
        audioRef.current = null;
      };

      await audio.play();
    } catch (error) {
      console.warn('Google TTS 失敗，使用瀏覽器語音合成', error);
      // 備用：使用瀏覽器語音合成
      if (synth) {
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = 'zh-TW';
        utterance.rate = 0.9;
        utterance.pitch = 0.8;  // 稍微降低音調模擬老人聲音
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
      }
    }
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
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    if (synth) {
      synth.cancel();
    }
    setIsSpeaking(false);
    setCurrentSubtitle('');
  };

  // 拍照功能
  const startCamera = async () => {
    try {
      // 先顯示相機介面
      setShowCamera(true);
      
      // 等待 DOM 更新後再獲取攝影機流
      await new Promise(resolve => setTimeout(resolve, 100));
      
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: { 
          facingMode: 'user',
          width: { ideal: 1280 },
          height: { ideal: 720 }
        } 
      });
      
      streamRef.current = stream;
      
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        // 確保 video 元素播放
        videoRef.current.onloadedmetadata = () => {
          if (videoRef.current) {
            videoRef.current.play().catch(err => {
              console.error('無法播放視頻:', err);
            });
          }
        };
      }
    } catch (error: any) {
      console.error('無法開啟攝影機:', error);
      setShowCamera(false);
      
      let errorMessage = '無法開啟攝影機，請確認已授予權限';
      if (error.name === 'NotAllowedError') {
        errorMessage = '攝影機權限被拒絕，請在瀏覽器設定中允許攝影機存取';
      } else if (error.name === 'NotFoundError') {
        errorMessage = '找不到攝影機，請確認攝影機已連接';
      } else if (error.name === 'NotReadableError') {
        errorMessage = '攝影機被其他應用程式使用中';
      }
      alert(errorMessage);
    }
  };

  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setShowCamera(false);
  };

  const capturePhoto = async () => {
    if (!videoRef.current) {
      alert('攝影機未就緒，請稍候再試');
      return;
    }

    const video = videoRef.current;
    
    // 檢查視頻是否已載入
    if (video.readyState !== video.HAVE_ENOUGH_DATA) {
      alert('攝影機畫面尚未載入完成，請稍候再試');
      return;
    }

    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth || 1280;
    canvas.height = video.videoHeight || 720;
    const ctx = canvas.getContext('2d');
    if (!ctx) {
      alert('無法創建畫布');
      return;
    }

    // 鏡像翻轉回來（因為顯示時是鏡像的）
    ctx.translate(canvas.width, 0);
    ctx.scale(-1, 1);
    ctx.drawImage(video, 0, 0);
    const imageBase64 = canvas.toDataURL('image/jpeg', 0.9).split(',')[1]; // 移除 data:image/jpeg;base64, 前綴

    stopCamera();
    setIsProcessingPhoto(true);

    try {
      // 調用變老 API
      const response = await axios.post(`${API_BASE_URL}/api/age-photo`, {
        image_base64: imageBase64,
        target_age: 75,
        mock: false
      });

      if (response.data.success && response.data.aged_image_base64) {
        const agedPhoto = `data:image/jpeg;base64,${response.data.aged_image_base64}`;
        setAgedPhotoUrl(agedPhoto);
        sessionStorage.setItem('agedPhotoUrl', agedPhoto);
      } else {
        throw new Error('變老處理失敗');
      }
    } catch (error) {
      console.error('變老處理失敗:', error);
      alert('變老處理失敗，請稍後再試');
    } finally {
      setIsProcessingPhoto(false);
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
        <Mascot 
          isSpeaking={isSpeaking} 
          text={currentSubtitle} 
          agedPhotoUrl={agedPhotoUrl}
        />
        
        {/* 拍照介面 */}
        {showCamera && !agedPhotoUrl && (
          <div className="camera-overlay">
            <div className="camera-container">
              <h3>請看向鏡頭，準備拍照</h3>
              <video 
                ref={videoRef} 
                autoPlay 
                playsInline 
                muted
                className="camera-video"
                style={{ transform: 'scaleX(-1)' }} // 鏡像顯示
              />
              <div className="camera-buttons">
                <button onClick={capturePhoto} className="capture-button">
                  拍照
                </button>
                <button onClick={stopCamera} className="cancel-button">
                  取消
                </button>
              </div>
            </div>
          </div>
        )}

        {/* 處理中提示 */}
        {isProcessingPhoto && (
          <div className="processing-overlay">
            <div className="processing-message">
              <p>正在處理照片，請稍候...</p>
            </div>
          </div>
        )}

        {/* 如果還沒有拍照，顯示提示 */}
        {!agedPhotoUrl && !showCamera && messages.length === 0 && (
          <div className="photo-prompt">
            <p>👋 歡迎！請先拍照，看看變老後的自己</p>
            <button onClick={startCamera} className="start-camera-button">
              📷 開始拍照
            </button>
          </div>
        )}
        
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

