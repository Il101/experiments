# 🔥 Live Activity Feed - Quick Reference

## 📖 USAGE GUIDE

### Basic Usage

```typescript
import { LiveActivityFeed } from '../components/activity';
import { useActivityFeed } from '../hooks/useActivityFeed';

function MyPage() {
  const { events, addEvent } = useActivityFeed({ maxEvents: 20 });
  
  return (
    <LiveActivityFeed 
      events={events}
      maxEvents={20}
      autoScroll={true}
      showTimestamp={true}
    />
  );
}
```

### Adding Events Manually

```typescript
// Add a scan event
addEvent({
  type: 'scan',
  severity: 'info',
  message: 'Scanning BTCUSDT (45/100)',
  symbol: 'BTCUSDT',
  details: { progress: '45/100', stage: 'breakout_check' }
});

// Add an entry event
addEvent({
  type: 'entry',
  severity: 'success',
  message: 'Entry: LONG BTCUSDT @ $44000',
  symbol: 'BTCUSDT',
  details: { side: 'LONG', entry: 44000, size: 0.5 }
});

// Add an error event
addEvent({
  type: 'error',
  severity: 'error',
  message: 'Failed to place order',
  details: { error_code: 'INSUFFICIENT_BALANCE' }
});
```

### Transform Logs to Events

```typescript
import { transformLogToActivity } from '../hooks/useActivityFeed';

const { data: logs } = useLogs({ limit: 50 });

useEffect(() => {
  if (logs) {
    logs.forEach((log) => {
      const event = transformLogToActivity(log);
      addEvent(event);
    });
  }
}, [logs]);
```

### WebSocket Integration (Future)

```typescript
const { events, isConnected } = useActivityFeed({
  maxEvents: 50,
  autoConnect: true,
  wsUrl: 'ws://localhost:8000/ws/events'
});

// Backend WebSocket endpoint example:
@router.websocket("/ws/events")
async def websocket_events(websocket: WebSocket):
    await websocket.accept()
    while True:
        event = await event_queue.get()
        await websocket.send_json({
            "type": "activity_event",
            "payload": {
                "type": "entry",
                "severity": "success",
                "message": "Entry: LONG BTCUSDT @ $44000",
                "symbol": "BTCUSDT"
            }
        })
```

### Compact Version

```typescript
import { CompactActivityFeed } from '../components/activity';

<CompactActivityFeed 
  events={events}
  maxEvents={5}
/>
```

## 🎨 EVENT TYPES

### Available Types

| Type | Icon | Description | Example |
|------|------|-------------|---------|
| `scan` | 🔍 | Scanning symbols | "Scanning BTCUSDT (45/100)" |
| `candidate` | ⭐ | Candidate found | "SOLUSDT found! Score: 0.85" |
| `signal` | 📊 | Signal generated | "LONG signal for BTCUSDT" |
| `entry` | 📈 | Position entry | "Entry: LONG @ $44000" |
| `exit` | ✅ | Position exit | "Exit: @ $120 (+2.5R)" |
| `reject` | ❌ | Rejected signal | "Rejected: volume too low" |
| `error` | 🔴 | Error occurred | "WebSocket connection lost" |
| `info` | ℹ️ | Information | "Engine started" |
| `level_building` | 📏 | Building levels | "Building levels for ADAUSDT" |
| `sizing` | 📐 | Size calculation | "Position size: 0.5 BTC" |

### Severity Levels

| Severity | Color | Badge | Use Case |
|----------|-------|-------|----------|
| `info` | 🔵 Blue | Info | General information |
| `success` | 🟢 Green | Success | Positive events (entry, exit) |
| `warning` | 🟡 Yellow | Warning | Cautions, rejections |
| `error` | 🔴 Red | Danger | Errors, failures |

## 📋 PROPS REFERENCE

### LiveActivityFeed Props

```typescript
interface LiveActivityFeedProps {
  events: ActivityEvent[];        // Array of events to display
  maxEvents?: number;             // Maximum events to show (default: 20)
  autoScroll?: boolean;           // Auto-scroll to new (default: true)
  showTimestamp?: boolean;        // Show timestamps (default: true)
  className?: string;             // Additional CSS classes
}
```

### ActivityEvent Interface

```typescript
interface ActivityEvent {
  id: string;                     // Unique identifier (auto-generated)
  timestamp: string;              // ISO timestamp (auto-generated)
  type: EventType;                // Event type (scan, entry, etc)
  message: string;                // Display message
  details?: Record<string, any>;  // Additional metadata
  severity: Severity;             // info | success | warning | error
  symbol?: string;                // Trading symbol (optional)
}
```

### useActivityFeed Options

```typescript
interface UseActivityFeedOptions {
  maxEvents?: number;             // Max events in state (default: 100)
  autoConnect?: boolean;          // Auto-connect WebSocket (default: false)
  wsUrl?: string;                 // WebSocket URL (optional)
}
```

## 🎯 EXAMPLES

### Example 1: Basic Dashboard Integration

```typescript
import { LiveActivityFeed } from '../components/activity';
import { useActivityFeed, transformLogToActivity } from '../hooks/useActivityFeed';
import { useLogs } from '../hooks';

export const Dashboard = () => {
  const { data: logs } = useLogs({ limit: 50 });
  const { events, addEvent } = useActivityFeed({ maxEvents: 20 });

  useEffect(() => {
    if (logs && logs.length > 0) {
      logs.slice(0, 5).forEach((log) => {
        addEvent(transformLogToActivity(log));
      });
    }
  }, [logs]);

  return (
    <div>
      <h1>Dashboard</h1>
      <LiveActivityFeed events={events} />
    </div>
  );
};
```

### Example 2: Manual Event Creation

```typescript
const { addEvent } = useActivityFeed();

// When scanning starts
addEvent({
  type: 'scan',
  severity: 'info',
  message: `Scanning ${symbol} (${progress}/100)`,
  symbol: symbol,
  details: { progress, stage: 'breakout_check' }
});

// When entry occurs
addEvent({
  type: 'entry',
  severity: 'success',
  message: `Entry: ${side} ${symbol} @ $${price}`,
  symbol: symbol,
  details: { side, entry: price, size, risk_r: 1.0 }
});

// When error occurs
addEvent({
  type: 'error',
  severity: 'error',
  message: `Failed: ${errorMessage}`,
  details: { error_code: code, stack: error.stack }
});
```

### Example 3: Compact Version in Card

```typescript
import { CompactActivityFeed } from '../components/activity';

<Card title="Recent Activity">
  <CompactActivityFeed 
    events={events}
    maxEvents={5}
  />
</Card>
```

### Example 4: Custom Styling

```typescript
<LiveActivityFeed 
  events={events}
  className="my-custom-feed"
/>

// custom.css
.my-custom-feed .activity-event {
  border-radius: 12px;
  padding: 1rem;
}

.my-custom-feed .event-icon {
  font-size: 1.5rem;
}
```

## 🔧 CUSTOMIZATION

### Custom Transform Function

```typescript
const customTransform = (data: any): Omit<ActivityEvent, 'id' | 'timestamp'> => {
  return {
    type: determineType(data),
    severity: determineSeverity(data),
    message: formatMessage(data),
    symbol: data.symbol,
    details: extractDetails(data)
  };
};

const event = customTransform(myData);
addEvent(event);
```

### Custom Timestamp Format

```typescript
// Edit LiveActivityFeed.tsx
const formatTimestamp = (timestamp: string) => {
  const date = new Date(timestamp);
  return date.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit'
  });
};
```

### Custom Event Colors

```css
/* Edit LiveActivityFeed.css */
.activity-event-success {
  border-left-color: #10b981; /* Custom green */
  background-color: rgba(16, 185, 129, 0.05);
}
```

## 🐛 TROUBLESHOOTING

### Events Not Showing
```typescript
// Check if events array is populated
console.log('Events:', events);

// Check if component is rendered
console.log('Component mounted');

// Verify logs are fetched
const { data: logs, isLoading } = useLogs();
console.log('Logs:', logs, 'Loading:', isLoading);
```

### Duplicate Events
```typescript
// Use event IDs to filter duplicates
const seenIds = new Set();
const uniqueEvents = events.filter(e => {
  if (seenIds.has(e.id)) return false;
  seenIds.add(e.id);
  return true;
});
```

### WebSocket Not Connecting
```typescript
const { isConnected, error } = useActivityFeed({
  autoConnect: true,
  wsUrl: 'ws://localhost:8000/ws/events'
});

console.log('Connected:', isConnected);
console.log('Error:', error);

// Check WebSocket URL
// Check backend WebSocket endpoint
// Check network/firewall
```

## 📚 ADDITIONAL RESOURCES

- **Component:** `frontend/src/components/activity/LiveActivityFeed.tsx`
- **Hook:** `frontend/src/hooks/useActivityFeed.ts`
- **Styles:** `frontend/src/components/activity/LiveActivityFeed.css`
- **Task Report:** `reports/UX/TASK_3_COMPLETED.md`
- **Session Summary:** `reports/UX/SESSION_2_SUMMARY.md`

## 🎉 QUICK TIPS

1. **Use transformLogToActivity** for consistent event creation
2. **Limit events** to prevent memory issues (maxEvents)
3. **Auto-scroll** for better UX (autoScroll: true)
4. **Show timestamps** for context (showTimestamp: true)
5. **Use severity colors** to guide user attention
6. **Add details** for debugging information
7. **Test empty state** (no events)
8. **Check responsive design** on mobile

---

**Happy coding! 🚀**
