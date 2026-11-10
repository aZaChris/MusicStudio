import Svg, { Circle, Line, Path, Polyline, Rect } from "react-native-svg";

const PATHS = {
  home: <Path d="M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6h-6v6H4a1 1 0 0 1-1-1z" />,
  students: (
    <>
      <Path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
      <Circle cx="9" cy="7" r="4" />
      <Path d="M23 21v-2a4 4 0 0 0-3-3.9" />
      <Path d="M16 3.1a4 4 0 0 1 0 7.8" />
    </>
  ),
  payments: (
    <>
      <Rect x="2" y="5" width="20" height="14" rx="2" />
      <Line x1="2" y1="10" x2="22" y2="10" />
    </>
  ),
  logout: (
    <>
      <Path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
      <Polyline points="16 17 21 12 16 7" />
      <Line x1="21" y1="12" x2="9" y2="12" />
    </>
  ),
  back: <Polyline points="15 18 9 12 15 6" />,
  forward: <Polyline points="9 18 15 12 9 6" />,
  check: <Polyline points="20 6 9 17 4 12" />,
  plus: (
    <>
      <Line x1="12" y1="5" x2="12" y2="19" />
      <Line x1="5" y1="12" x2="19" y2="12" />
    </>
  ),
  search: (
    <>
      <Circle cx="11" cy="11" r="7" />
      <Line x1="21" y1="21" x2="16.6" y2="16.6" />
    </>
  ),
  alert: (
    <>
      <Path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" />
      <Line x1="12" y1="9" x2="12" y2="13" />
      <Line x1="12" y1="17" x2="12" y2="17" />
    </>
  ),
  note: (
    <>
      <Path d="M9 18V5l12-2v13" />
      <Circle cx="6" cy="18" r="3" />
      <Circle cx="18" cy="16" r="3" />
    </>
  ),
} as const;

export type IconName = keyof typeof PATHS;

/** Stroke icon on a 24px grid. Decorative: the control around it carries the accessible name. */
export function Icon({ name, size = 20, color, strokeWidth = 2.2 }: { name: IconName; size?: number; color: string; strokeWidth?: number }) {
  return (
    <Svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke={color}
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      accessible={false}
      importantForAccessibility="no-hide-descendants"
    >
      {PATHS[name]}
    </Svg>
  );
}
