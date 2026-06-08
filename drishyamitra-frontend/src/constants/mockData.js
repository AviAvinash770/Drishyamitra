import { GP } from "../styles/theme";

export const MOCK_PERSONS = [
  { id: 1, name: "Priya Sharma", photoCount: 47, color: GP.purple, bg: GP.purpleLight, emoji: "👩", initials: "PS", tags: ["Family", "Vacation"] },
  { id: 2, name: "Rahul Verma", photoCount: 31, color: GP.blue, bg: GP.blueLight, emoji: "👨", initials: "RV", tags: ["Friends", "Events"] },
  { id: 3, name: "Grandma", photoCount: 23, color: GP.amber, bg: GP.amberLight, emoji: "👵", initials: "GM", tags: ["Family"] },
  { id: 4, name: "Ananya", photoCount: 18, color: GP.coral, bg: GP.coralLight, emoji: "👧", initials: "AN", tags: ["Family"] },
  { id: 5, name: "Dad", photoCount: 39, color: GP.teal, bg: GP.tealLight, emoji: "👨‍🦳", initials: "DD", tags: ["Family"] },
  { id: 6, name: "Unknown", photoCount: 6, color: GP.textTertiary, bg: GP.borderLight, emoji: "❓", initials: "?", tags: [] },
];

export const PHOTO_EMOJIS = ["🌄", "🎭", "🎊", "🤳", "📸", "🌺", "🎂", "💍", "✈️", "🏔️", "🌅", "🎉", "🏠", "🌸", "🎠", "🦋", "🌊", "🎪"];

export const PHOTO_PALETTES = [
  ["#e8d5b7", "#d4a574"], ["#b7d5e8", "#74a5d4"], ["#d5e8b7", "#a5d474"],
  ["#e8b7d5", "#d474a5"], ["#d5b7e8", "#a574d4"], ["#e8e0b7", "#d4c474"],
];

export const MOCK_PHOTOS = Array.from({ length: 24 }, (_, i) => ({
  id: i + 1,
  name: `IMG_${2025000 + i * 137}.JPG`,
  size: (Math.random() * 3 + 1).toFixed(1) + " MB",
  date: `2025-0${Math.floor(i / 8) + 1}-${String((i % 28) + 1).padStart(2, "0")}`,
  persons: MOCK_PERSONS.slice(0, Math.floor(Math.random() * 3) + 1).map(p => p.name),
  folder: ["Family Trips", "Weddings", "Festivals", "Birthdays", "Events"][i % 5],
  palette: PHOTO_PALETTES[i % PHOTO_PALETTES.length],
  emoji: PHOTO_EMOJIS[i % PHOTO_EMOJIS.length],
  recognized: Math.random() > 0.2,
  favorite: Math.random() > 0.7,
  height: [160, 200, 180, 220, 170][i % 5],
}));

export const FOLDERS = [
  { name: "Family Trips", count: 47, icon: "✈️", color: GP.blue, bg: GP.blueLight },
  { name: "Weddings", count: 123, icon: "💍", color: GP.coral, bg: GP.coralLight },
  { name: "Festivals", count: 89, icon: "🎉", color: GP.amber, bg: GP.amberLight },
  { name: "Birthdays", count: 56, icon: "🎂", color: GP.teal, bg: GP.tealLight },
  { name: "Events", count: 34, icon: "📸", color: GP.purple, bg: GP.purpleLight },
];

export const MEMORIES = [
  { label: "2 years ago", title: "Diwali 2023", count: 24, palette: PHOTO_PALETTES[0], emoji: "🪔" },
  { label: "Last Summer", title: "Manali Trip", count: 47, palette: PHOTO_PALETTES[1], emoji: "🏔️" },
  { label: "Best of April", title: "Birthday Bash", count: 18, palette: PHOTO_PALETTES[2], emoji: "🎂" },
  { label: "1 year ago", title: "Priya's Wedding", count: 89, palette: PHOTO_PALETTES[3], emoji: "💍" },
];
