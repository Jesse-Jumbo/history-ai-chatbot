import React, { useEffect, useState } from 'react';
import './Mascot.css';

interface MascotProps {
  isSpeaking: boolean;
  text: string; // 當前正在說的話
  agedPhotoUrl?: string | null; // 變老後的照片 URL（base64 或 URL）
}

type MouthShape = 'idle' | 'open' | 'half' | 'close';

const Mascot: React.FC<MascotProps> = ({ isSpeaking, text, agedPhotoUrl }) => {
  const [mouthShape, setMouthShape] = useState<MouthShape>('idle');

  useEffect(() => {
    if (!isSpeaking) {
      setMouthShape('idle');
      return;
    }

    // 根據文字長度和時間動態改變嘴形
    const interval = setInterval(() => {
      const shapes: MouthShape[] = ['open', 'half', 'close', 'half'];
      const index = Math.floor(Date.now() / 200) % shapes.length;
      setMouthShape(shapes[index]);
    }, 200);

    return () => clearInterval(interval);
  }, [isSpeaking, text]);

  // 如果有變老後的照片，顯示照片；否則顯示動畫頭像
  if (agedPhotoUrl) {
    return (
      <div className="mascot-container">
        <div className="mascot-photo">
          <img 
            src={agedPhotoUrl} 
            alt="變老後的自己" 
            className="aged-photo"
          />
          {isSpeaking && (
            <div className="speaking-indicator">
              <span className="speaking-dot"></span>
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="mascot-container">
      <div className="mascot">
        {/* 臉部 */}
        <div className="face">
          {/* 眼睛 */}
          <div className="eye left-eye"></div>
          <div className="eye right-eye"></div>
          
          {/* 嘴巴 - 根據 mouthShape 改變 */}
          <div className={`mouth mouth-${mouthShape}`}>
            {mouthShape === 'open' && <div className="mouth-inner"></div>}
            {mouthShape === 'half' && <div className="mouth-half"></div>}
            {mouthShape === 'close' && <div className="mouth-line"></div>}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Mascot;

