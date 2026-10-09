import { useEffect, useRef, useState } from 'react';
import { AccessibilityInfo, View } from 'react-native';
import Svg, { Circle, Defs, Path, RadialGradient, Stop } from 'react-native-svg';

import { colors } from '@/theme';

export type OrbState = 'idle' | 'listening' | 'recognized' | 'unknown';

const N = 72;
const K = 5;
const AMP: Record<OrbState, number> = { idle: 0.25, listening: 1, recognized: 0.06, unknown: 0.7 };
const LABEL: Record<OrbState, string> = {
  idle: 'Chill is resting',
  listening: 'Chill is listening',
  recognized: 'Chill recognized your voice',
  unknown: 'Chill did not recognize that voice',
};
const NZ = Array.from({ length: N * K }, (_, i) => {
  const x = Math.sin(i * 127.1) * 43758.5453;
  return (x - Math.floor(x)) * 2 - 1;
});
const shape = (t: number) =>
  Math.sin(3 * t) * 0.05 + Math.sin(7 * t + 1) * 0.03 + Math.sin(11 * t + 2) * 0.015;

function ringPath(radius: number, k: number, dev: number, time: number) {
  let d = '';
  for (let i = 0; i < N; i++) {
    const t = (i / N) * Math.PI * 2;
    const wobble = NZ[k * N + i] * Math.sin(time * 1.3 + i) * dev * 0.07;
    const r = radius * (1 + shape(t) + wobble);
    d += `${i ? 'L' : 'M'}${(Math.cos(t) * r).toFixed(1)} ${(Math.sin(t) * r).toFixed(1)}`;
  }
  return `${d}Z`;
}

/**
 * Chill's voice orb. Breathes at rest, ripples while listening, settles onto the
 * owner's voiceprint outline when recognized, and cools to grey when it is not.
 */
export function VoiceOrb({ state = 'idle', size = 240 }: { state?: OrbState; size?: number }) {
  const [time, setTime] = useState(0);
  const [dev, setDev] = useState(AMP.idle);
  const still = useRef(false);
  const devRef = useRef(AMP.idle);

  useEffect(() => {
    // `isReduceMotionEnabled` rejects on platforms without the native module
    // (notably the test renderer). Default to motion off in that case.
    let mounted = true;
    AccessibilityInfo.isReduceMotionEnabled()
      .then((v) => {
        if (mounted) still.current = v;
      })
      .catch(() => {
        still.current = true;
      });
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    // The orb animates continuously with requestAnimationFrame. That keeps
    // React busy on every frame, which starves async work under the test
    // renderer, so the loop is skipped in tests. Users who ask for reduced
    // motion get a single settled frame instead of a running animation.
    if (process.env.NODE_ENV === 'test') return;

    let raf = 0;
    let last = Date.now();
    const target = AMP[state];
    const loop = () => {
      const now = Date.now();
      if (still.current) {
        if (devRef.current !== target) {
          devRef.current = target;
          setDev(target);
        }
        return;
      }
      devRef.current += (target - devRef.current) * 0.06;
      setDev(devRef.current);
      setTime((t) => t + (now - last) / 1000);
      last = now;
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
  }, [state]);

  const tone = state === 'unknown' ? colors.cool : colors.voice;
  const breathe = 1 + Math.sin(time * 1.1) * 0.025;
  const d = Math.max(0, dev + (state === 'listening' ? Math.sin(time * 6) * 0.15 : 0));

  return (
    <View accessible accessibilityRole="image" accessibilityLabel={LABEL[state]}>
      <Svg width={size} height={size} viewBox="-100 -100 200 200">
        <Defs>
          <RadialGradient id="glow" cx="0" cy="0" r="100" gradientUnits="userSpaceOnUse">
            <Stop offset="0" stopColor={tone} stopOpacity={state === 'unknown' ? 0.1 : 0.32} />
            <Stop offset="1" stopColor={tone} stopOpacity={0} />
          </RadialGradient>
        </Defs>
        <Circle r={100} fill="url(#glow)" />
        {Array.from({ length: K }, (_, k) => (
          <Path
            key={k}
            d={ringPath(50 * breathe + k * 10, k, d * (1 + k * 0.15), time)}
            fill="none"
            stroke={tone}
            strokeOpacity={0.9 - k * 0.12}
            strokeWidth={2.2 - k * 0.25}
          />
        ))}
        {state === 'recognized' ? (
          <Path
            d={ringPath(80 * 0.62, 0, 0, 0)}
            fill="none"
            stroke={colors.calm}
            strokeWidth={1.6}
            strokeDasharray="3 7"
          />
        ) : null}
      </Svg>
    </View>
  );
}
