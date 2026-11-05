import React from 'react';
import {Composition} from 'remotion';
import {HermesShowcase} from './HermesShowcase';

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="HermesHackathonShowcase"
        component={HermesShowcase}
        durationInFrames={2250}
        fps={30}
        width={1920}
        height={1080}
      />
    </>
  );
};
