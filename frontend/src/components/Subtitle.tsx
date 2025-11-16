import React from 'react';
import './Subtitle.css';

interface SubtitleProps {
  text: string;
  isVisible: boolean;
}

const Subtitle: React.FC<SubtitleProps> = ({ text, isVisible }) => {
  if (!isVisible || !text) return null;

  return (
    <div className="subtitle-container">
      <div className="subtitle">
        {text}
      </div>
    </div>
  );
};

export default Subtitle;

