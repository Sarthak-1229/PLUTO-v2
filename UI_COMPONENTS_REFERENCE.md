# PLUTO v2 - Complete UI/UX Component Reference

## Design System

### Color Palette
| Token | Value | Usage |
|-------|-------|-------|
| `--primary` | `#4F46E5` | Primary buttons, active states, links |
| `--primary-light` | `#818CF8` | Hover states, accents |
| `--surface` | `#F8FAFC` | Page background |
| `--surface-card` | `#FFFFFF` | Card backgrounds |
| `--text-primary` | `#0F172A` | Headings, body text |
| `--text-secondary` | `#64748B` | Secondary text, labels |
| `--border` | `#E2E8F0` | Borders, dividers |
| `--success` | `#22C55E` | Online status, success states |
| `--warning` | `#F59E0B` | VRAM warning (>60%) |
| `--danger` | `#EF4444` | VRAM critical (>80%), errors |

### Typography
- **Font Family**: Inter (Google Fonts)
- **Weights**: 300 (light), 400 (regular), 500 (medium), 600 (semibold), 700 (bold)
- **Base Size**: 14px body, 16px headings

### Spacing Scale
- `xs`: 4px
- `sm`: 8px
- `md`: 12px
- `lg`: 16px
- `xl`: 24px
- `2xl`: 32px

---

## Layout Structure

### Overall Layout
- **Type**: Flexbox, full-height screen
- **Structure**: Sidebar (fixed) + Main Content (flex-1)
- **Total Height**: 100vh
- **Background**: `#F8FAFC`

```
┌─────────────┬─────────────────────────────────────┐
│             │                                     │
│   SIDEBAR   │          MAIN CONTENT               │
│   256px     │           flex-1                    │
│             │                                     │
│  • Logo     │  • Header                           │
│  • Nav      │  • Chat Area                        │
│  • Stats    │  • Input Area                       │
│  • Actions  │                                     │
│  • Settings │                                     │
│  • Status   │                                     │
│             │                                     │
└─────────────┴─────────────────────────────────────┘
```

---

## Component List

### 1. SIDEBAR
**Container**
- Width: 256px (w-64)
- Background: White (`#FFFFFF`)
- Border-right: 1px solid `#E2E8F0`
- Display: Flex column
- Height: 100vh

**1.1 Logo Section**
- Padding: 16px
- Border-bottom: 1px solid `#F1F5F9`
- Layout: Flex row, gap 12px
- **Icon Box**
  - Size: 32x32px
  - Background: `#4F46E5`
  - Border-radius: 8px
  - Icon: Orbit (Lucide), 20x20px, white
- **Text**
  - Title: "PLUTO v2", font-semibold, 14px, `#0F172A`
  - Subtitle: "Research Assistant", font-regular, 12px, `#64748B`

**1.2 Navigation Pills**
- Container: Flex, background `#F8FAFC`, border 1px `#E2E8F0`, border-radius 8px, padding 4px
- **Each Nav Item**
  - Padding: 6px 12px
  - Border-radius: 6px
  - Font-size: 13px
  - Font-weight: 500
  - Color: `#64748B`
  - Hover: background `#FFFFFF`
  - Active state:
    - Background: `#FFFFFF`
    - Color: `#4F46E5`
    - Box-shadow: 0 1px 2px rgba(0,0,0,0.05)
- **Items**: Chat, Research, Reports
- Each with Lucide icon (message-square, search, file-text)

**1.3 Stats Section**
- Padding: 12px 16px
- Border-bottom: 1px solid `#F1F5F9`
- **Knowledge Card**
  - Background: `#F8FAFC`
  - Border-radius: 8px
  - Padding: 8px
  - Label: "Knowledge", 11px, `#64748B`
  - Value: Large bold, `#0F172A`
- **VRAM Card**
  - Same as Knowledge
  - Label: "VRAM"
  - Value: Shows "0 MB" or actual usage
- **GPU Memory Bar**
  - Container: Full width, height 6px, background `#E2E8F0`, border-radius 4px
  - Fill: Animated progress bar
    - Width: Dynamic based on usage
    - Color: Green (`#22C55E`) < 60%, Orange (`#F59E0B`) 60-80%, Red (`#EF4444`) > 80%
  - Labels: "GPU Memory" (left), "77%" (right), "4703 MB / 6141 MB" (below)

**1.4 Quick Actions**
- Padding: 12px 16px
- Border-bottom: 1px solid `#F1F5F9`
- Title: "QUICK ACTIONS", 11px, uppercase, tracking-wider, `#64748B`
- **Action Buttons** (stacked vertically)
  - Layout: Flex row, gap 8px
  - Padding: 8px 12px
  - Border-radius: 8px
  - Font-size: 14px
  - Color: `#64748B`
  - Hover: Background `#F8FAFC`
  - Icons: cloud, newspaper, flask-conical, smile (Lucide, 16x16px)
  - Text: Weather, News, Research, Joke

**1.5 Settings**
- Padding: 12px 16px
- Title: "SETTINGS", 11px, uppercase, `#64748B`
- **Voice Selector**
  - Label: "Voice", 14px, `#64748B`
  - Select dropdown: 12px, border `#E2E8F0`, rounded
  - Options: Aria, Guy, Sonia
- **Auto-play Toggle**
  - Label: "Auto-play", 14px, `#64748B`
  - Checkbox: Standard HTML checkbox

**1.6 Status Indicator**
- Padding: 16px
- Border-top: 1px solid `#F1F5F9`
- Layout: Flex row, gap 8px
- **Status Dot**
  - Size: 8x8px
  - Border-radius: 50%
  - Color: Green (`#22C55E`) when online, Red (`#EF4444`) when offline
- **Status Text**
  - Font-size: 12px
  - Color: `#64748B`
  - Text: "Online" or "Offline"

---

### 2. HEADER
**Container**
- Height: 56px
- Border-bottom: 1px solid `#E2E8F0`
- Background: White
- Padding: 0 24px
- Display: Flex row, align-center

**2.1 Title Section**
- Title: "Research Chat", font-semibold, 16px, `#0F172A`
- Subtitle: "Ask anything - AI searches the web for answers", 12px, `#64748B`

**2.2 Voice Button**
- Class: `.btn.btn-secondary`
- Icon: Mic (Lucide)
- Text: "Voice"
- On click: Starts/stops speech recognition
- Active state: Background `#FEF2F2` (light red)

---

### 3. CHAT AREA
**Container**
- ID: `chatArea`
- Display: Flex column
- Overflow-y: Auto
- Padding: 24px
- Gap: 16px

**3.1 Welcome Message**
- Layout: Flex row, gap 12px
- Animation: Fade in (0.2s)
- **Avatar**
  - Size: 32x32px
  - Background: `#4F46E5`
  - Icon: Orbit, white
- **Message Bubble**
  - Class: `.card`
  - Padding: 16px
  - Border-radius-top-left: 0
  - **Text**: "Hello! I'm PLUTO v2..." 14px, `#64748B`
  - **Quick Action Buttons**:
    - Quantum Computing (atom icon)
    - Research Report (file-text icon)
    - Space News (telescope icon)

**3.2 User Message**
- Layout: Flex row-reverse
- **Avatar**: User icon (Lucide), gray background
- **Bubble**: Light blue background (`#EEF2FF`), right-aligned, max-width 80%

**3.3 Assistant Message**
- Layout: Flex row
- **Avatar**: Orbit icon, indigo background
- **Bubble**: White background, left-aligned, max-width 90%
- **Content**:
  - Text: 14px, `#64748B`, whitespace-pre-wrap
  - Audio player: Standard HTML5 audio with controls
- **Animations**: Fade-in on appearance

---

### 4. INPUT AREA
**Container**
- Border-top: 1px solid `#E2E8F0`
- Background: White
- Padding: 16px 24px

**4.1 Input Row**
- Layout: Flex row, gap 12px
- **Textarea**
  - Class: `.input`
  - Rows: 2
  - Placeholder: "Ask a research question..."
  - Border-radius: 10px
  - Focus: Border-color `#4F46E5`, box-shadow ring
- **Send Button**
  - Class: `.btn.btn-primary`
  - Icon: Send (Lucide)
  - Text: "Send"
  - Loading state: Shows spinner instead of icon
  - Disabled when loading

**4.2 Status Bar**
- Layout: Flex row, justify-between
- **Left**: Last activity time ("Last: Just now")
- **Right**: Search progress indicator
  - Progress bar: Hidden by default, shows during search
  - Status text: "Searching...", "Done", "Error"

---

### 5. BUTTON COMPONENTS

**.btn (Base)**
- Display: Inline-flex
- Align-items: Center
- Gap: 8px
- Padding: 8px 16px
- Border-radius: 8px
- Font-size: 14px
- Font-weight: 500
- Transition: All 0.15s ease
- Cursor: Pointer
- Border: none

**.btn-primary**
- Background: `#4F46E5`
- Color: White
- Hover: Background `#4338CA`

**.btn-secondary**
- Background: `#F8FAFC`
- Color: `#64748B`
- Border: 1px solid `#E2E8F0`
- Hover: Background `#F1F5F9`

**.btn-icon**
- Padding: 8px
- Background: `#F8FAFC`
- Color: `#64748B`
- Hover: Background `#F1F5F9`, Color `#4F46E5`

---

### 6. CARD COMPONENT

**.card**
- Background: `#FFFFFF`
- Border-radius: 12px
- Border: 1px solid `#E2E8F0`
- Box-shadow: 0 1px 3px rgba(0,0,0,0.05)

---

### 7. SOURCE BADGE

**.source-badge**
- Display: Inline-flex
- Align-items: Center
- Gap: 4px
- Padding: 2px 8px
- Border-radius: 4px
- Font-size: 11px
- Font-weight: 500
- Background: `#EEF2FF`
- Color: `#4F46E5`

---

### 8. LOADING SPINNER

**.spinner**
- Width: 16px
- Height: 16px
- Border: 2px solid `#E2E8F0`
- Border-top-color: `#4F46E5`
- Border-radius: 50%
- Animation: Spin 0.8s linear infinite

---

### 9. AUDIO PLAYER
- Width: 100%
- Height: 32px
- Border-radius: 6px
- Standard HTML5 audio element

---

### 10. SCROLLBAR
- Width: 6px
- Track: Transparent
- Thumb: `#E2E8F0`, border-radius 3px
- Thumb hover: `#CBD5E1`

---

### 11. ANIMATIONS

**.fade-in**
- Animation: fadeIn 0.2s ease
- Keyframes: Opacity 0→1, TranslateY 8px→0

**Progress Bar**
- Transition: Width 0.3s ease

---

## Interactive States

| State | Background | Border | Text Color |
|-------|-----------|--------|------------|
| Default | `#F8FAFC` | `#E2E8F0` | `#64748B` |
| Hover | `#F1F5F9` | `#E2E8F0` | `#4F46E5` |
| Active/Focus | `#FFFFFF` | `#4F46E5` | `#4F46E5` |
| Disabled | `#F8FAFC` | `#E2E8F0` | `#94A3B8` |

---

## Responsive Behavior

- **Desktop**: Full sidebar + main content (current implementation)
- **Mobile**: Sidebar would collapse to hamburger menu (to be implemented)

---

## Icon Library
**Lucide Icons** (CDN loaded)
- orbit - Logo
- message-square - Chat tab
- search - Research tab
- file-text - Reports tab
- cloud - Weather quick action
- newspaper - News quick action
- flask-conical - Research quick action
- smile - Joke quick action
- mic - Voice input
- send - Send button
- user - User avatar
- atom - Quantum computing suggestion
- telescope - Space news suggestion

---

## APIs Endpoints Used

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/process` | POST | Send query, get answer + audio |
| `/vram` | GET | Get GPU memory usage |
| `/knowledge/stats` | GET | Get knowledge base stats |
| `/status` | GET | Get server status |
| `/health` | GET | Health check |

---

## JavaScript Functions

| Function | Purpose |
|----------|---------|
| `sendQuery()` | Send user query to backend |
| `toggleVoice()` | Start/stop voice recording |
| `playAudio(uri)` | Play audio response |
| `quickAction(type)` | Execute quick action button |
| `sendQuick(text)` | Send quick suggestion |
| `addMessage(role, text, audioUri)` | Add message to chat |
| `addToHistory(query, answer)` | Store in conversation history |
| `setLoading(state)` | Update send button state |
| `animateProgress()` | Animate search progress bar |
| `switchTab(tab)` | Switch navigation tab |
| `changeVoice(voice)` | Change TTS voice |
| `toggleAutoPlay(enabled)` | Toggle auto-play audio |

---

## Data Flow

```
User types query → Click Send → POST /process
                                    ↓
                         LLM generates answer
                                    ↓
                         TTS synthesizes audio
                                    ↓
                         Returns {answer, audio_uri}
                                    ↓
                    Display answer + play audio
```

---

## Notes for Stitch Implementation

1. **Use Auto Layout** for all containers
2. **Componentize** repeated elements (buttons, cards, nav items)
3. **Style Guide**: Create a text style for each weight/size combination
4. **Interactive States**: Design default, hover, active, disabled for buttons
5. **Responsive**: Consider mobile breakpoint where sidebar collapses
6. **Animations**: Add fade-in animation for new messages
7. **Icons**: Use Lucide icon set or equivalent
