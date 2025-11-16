import React, { useEffect, useState } from 'react';
import './Mascot.css';

interface MascotProps {
  isSpeaking: boolean;
  text: string; // 當前正在說的話
}

type MouthShape = 'idle' | 'open' | 'half' | 'close';

const Mascot: React.FC<MascotProps> = ({ isSpeaking, text }) => {
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

