import { Stack } from "expo-router";

// Both screens draw their own header (large title, back button), so the stack shows none.
export default function RosterLayout() {
  return <Stack screenOptions={{ headerShown: false, animation: "slide_from_right", animationDuration: 220 }} />;
}
