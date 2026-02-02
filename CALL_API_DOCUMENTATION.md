# Event Call API Documentation

## Overview
This guide explains how to implement real-time voice/video calling functionality for events using the Call API. Users can start calls, join/leave calls, and check who's currently in a call.

---

## Call Management Endpoints

### 1. Start a Call
**Endpoint:** `POST /api/v1/messages/{event_id}/call/start`

**Description:** Start a new call for an event. Only one call can be live per event at a time.

**Authentication:** Required (Bearer Token)

**Path Parameters:**
- `event_id` (string, required): The event identifier

**Headers:**
```http
Authorization: Bearer <your_access_token>
Content-Type: application/json
```

**Request Body:** Empty (none required)

**Success Response (200 OK):**
```json
{
  "status": "success",
  "message": "Call started",
  "event_id": "event_123",
  "call_info": {
    "event_id": "event_123",
    "is_live": true,
    "participant_count": 1,
    "participants": [
      {
        "user_id": 1,
        "full_name": "John Doe",
        "username": "johndoe",
        "joined_at": "2026-02-02T10:30:00"
      }
    ],
    "started_at": "2026-02-02T10:30:00",
    "initiator_id": 1
  }
}
```

**Error Responses:**

400 Bad Request:
```json
{
  "detail": "A call is already active for this event"
}
```

403 Forbidden:
```json
{
  "detail": "You must join the event to start a call"
}
```

404 Not Found:
```json
{
  "detail": "Event not found"
}
```

---

### 2. Join a Call
**Endpoint:** `POST /api/v1/messages/{event_id}/call/join`

**Description:** Join an active call for an event.

**Authentication:** Required (Bearer Token)

**Path Parameters:**
- `event_id` (string, required): The event identifier

**Headers:**
```http
Authorization: Bearer <your_access_token>
Content-Type: application/json
```

**Request Body:** Empty (none required)

**Success Response (200 OK):**
```json
{
  "status": "success",
  "message": "Joined call",
  "event_id": "event_123",
  "call_info": {
    "event_id": "event_123",
    "is_live": true,
    "participant_count": 2,
    "participants": [
      {
        "user_id": 1,
        "full_name": "John Doe",
        "username": "johndoe",
        "joined_at": "2026-02-02T10:30:00"
      },
      {
        "user_id": 2,
        "full_name": "Jane Smith",
        "username": "janesmith",
        "joined_at": "2026-02-02T10:31:00"
      }
    ],
    "started_at": "2026-02-02T10:30:00",
    "initiator_id": 1
  }
}
```

**Error Response:**

400 Bad Request:
```json
{
  "detail": "No active call for this event"
}
```

---

### 3. Leave a Call
**Endpoint:** `POST /api/v1/messages/{event_id}/call/leave`

**Description:** Leave an active call. If you're the last person, the call ends automatically.

**Authentication:** Required (Bearer Token)

**Path Parameters:**
- `event_id` (string, required): The event identifier

**Headers:**
```http
Authorization: Bearer <your_access_token>
Content-Type: application/json
```

**Request Body:** Empty (none required)

**Success Response (200 OK):**
```json
{
  "status": "success",
  "message": "Left call",
  "event_id": "event_123",
  "call_info": {
    "event_id": "event_123",
    "is_live": true,
    "participant_count": 1,
    "participants": [
      {
        "user_id": 1,
        "full_name": "John Doe",
        "username": "johndoe",
        "joined_at": "2026-02-02T10:30:00"
      }
    ],
    "started_at": "2026-02-02T10:30:00",
    "initiator_id": 1
  }
}
```

**Error Response:**

400 Bad Request:
```json
{
  "detail": "You are not in a call for this event"
}
```

---

### 4. End a Call
**Endpoint:** `POST /api/v1/messages/{event_id}/call/end`

**Description:** End the active call. Only the call initiator can end the call.

**Authentication:** Required (Bearer Token)

**Path Parameters:**
- `event_id` (string, required): The event identifier

**Headers:**
```http
Authorization: Bearer <your_access_token>
Content-Type: application/json
```

**Request Body:** Empty (none required)

**Success Response (200 OK):**
```json
{
  "status": "success",
  "message": "Call ended",
  "event_id": "event_123"
}
```

**Error Responses:**

400 Bad Request:
```json
{
  "detail": "No active call for this event"
}
```

403 Forbidden:
```json
{
  "detail": "Only the call initiator can end the call"
}
```

---

### 5. Get Call Status
**Endpoint:** `GET /api/v1/messages/{event_id}/call/status`

**Description:** Check the current call status for an event. Returns whether a call is live, how many people are in it, and who they are.

**Authentication:** Required (Bearer Token)

**Path Parameters:**
- `event_id` (string, required): The event identifier

**Headers:**
```http
Authorization: Bearer <your_access_token>
Content-Type: application/json
```

**Success Response (200 OK):**

When call is active:
```json
{
  "event_id": "event_123",
  "is_live": true,
  "participant_count": 3,
  "participants": [
    {
      "user_id": 1,
      "full_name": "John Doe",
      "username": "johndoe",
      "joined_at": "2026-02-02T10:30:00"
    },
    {
      "user_id": 2,
      "full_name": "Jane Smith",
      "username": "janesmith",
      "joined_at": "2026-02-02T10:31:00"
    },
    {
      "user_id": 3,
      "full_name": "Bob Johnson",
      "username": "bobjohnson",
      "joined_at": "2026-02-02T10:32:15"
    }
  ],
  "started_at": "2026-02-02T10:30:00",
  "initiator_id": 1
}
```

When no call is active:
```json
{
  "event_id": "event_123",
  "is_live": false,
  "participant_count": 0,
  "participants": [],
  "started_at": null
}
```

---

## Complete Call Workflow Example

### Step 1: Check if a call is already active
```javascript
async function checkCallStatus(eventId, accessToken) {
  const response = await fetch(`/api/v1/messages/${eventId}/call/status`, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json'
    }
  });
  
  return await response.json();
}

const status = await checkCallStatus('event_123', accessToken);
console.log(`Call is ${status.is_live ? 'LIVE' : 'NOT LIVE'}`);
console.log(`Participants: ${status.participant_count}`);
```

### Step 2: Start a call (if not already active)
```javascript
async function startCall(eventId, accessToken) {
  const response = await fetch(`/api/v1/messages/${eventId}/call/start`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json'
    }
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail);
  }
  
  return await response.json();
}

try {
  const result = await startCall('event_123', accessToken);
  console.log('Call started:', result);
} catch (error) {
  console.error('Error starting call:', error.message);
  // If error is "already active", just join the existing call
}
```

### Step 3: Join the call
```javascript
async function joinCall(eventId, accessToken) {
  const response = await fetch(`/api/v1/messages/${eventId}/call/join`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json'
    }
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail);
  }
  
  return await response.json();
}

const joinResult = await joinCall('event_123', accessToken);
console.log('Participants:', joinResult.call_info.participants);
```

### Step 4: Periodically check participant count
```javascript
async function monitorCall(eventId, accessToken, intervalMs = 3000) {
  setInterval(async () => {
    const status = await checkCallStatus(eventId, accessToken);
    
    console.log(`📞 Live Call: ${status.is_live}`);
    console.log(`👥 Participants: ${status.participant_count}`);
    
    // Update UI with participant list
    updateParticipantUI(status.participants);
    
    // If call ended, clean up
    if (!status.is_live && previouslyActive) {
      handleCallEnded();
    }
  }, intervalMs);
}
```

### Step 5: Leave the call
```javascript
async function leaveCall(eventId, accessToken) {
  const response = await fetch(`/api/v1/messages/${eventId}/call/leave`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json'
    }
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail);
  }
  
  return await response.json();
}

await leaveCall('event_123', accessToken);
console.log('You left the call');
```

---

## React Component Example

```jsx
import React, { useState, useEffect } from 'react';
import { Phone, PhoneOff, Users } from 'lucide-react';

function EventCall({ eventId, accessToken }) {
  const [callStatus, setCallStatus] = useState(null);
  const [isInCall, setIsInCall] = useState(false);
  const [loading, setLoading] = useState(false);
  const [participants, setParticipants] = useState([]);

  // Fetch call status
  const fetchCallStatus = async () => {
    try {
      const response = await fetch(`/api/v1/messages/${eventId}/call/status`, {
        headers: { 'Authorization': `Bearer ${accessToken}` }
      });
      const data = await response.json();
      setCallStatus(data);
      setParticipants(data.participants || []);
    } catch (error) {
      console.error('Error fetching call status:', error);
    }
  };

  // Poll for status updates
  useEffect(() => {
    fetchCallStatus();
    const interval = setInterval(fetchCallStatus, 3000);
    return () => clearInterval(interval);
  }, [eventId, accessToken]);

  // Start call
  const handleStartCall = async () => {
    setLoading(true);
    try {
      const response = await fetch(`/api/v1/messages/${eventId}/call/start`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${accessToken}` }
      });
      
      if (response.ok) {
        const data = await response.json();
        setIsInCall(true);
        setCallStatus(data.call_info);
      } else {
        const error = await response.json();
        alert(error.detail);
      }
    } catch (error) {
      console.error('Error starting call:', error);
    } finally {
      setLoading(false);
    }
  };

  // Join call
  const handleJoinCall = async () => {
    setLoading(true);
    try {
      const response = await fetch(`/api/v1/messages/${eventId}/call/join`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${accessToken}` }
      });
      
      if (response.ok) {
        const data = await response.json();
        setIsInCall(true);
        setCallStatus(data.call_info);
      } else {
        const error = await response.json();
        alert(error.detail);
      }
    } catch (error) {
      console.error('Error joining call:', error);
    } finally {
      setLoading(false);
    }
  };

  // Leave call
  const handleLeaveCall = async () => {
    setLoading(true);
    try {
      await fetch(`/api/v1/messages/${eventId}/call/leave`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${accessToken}` }
      });
      setIsInCall(false);
      fetchCallStatus();
    } catch (error) {
      console.error('Error leaving call:', error);
    } finally {
      setLoading(false);
    }
  };

  if (!callStatus) {
    return <div>Loading...</div>;
  }

  return (
    <div className="p-4 bg-white rounded-lg border border-gray-200">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          {callStatus.is_live ? (
            <>
              <div className="w-3 h-3 bg-red-500 rounded-full animate-pulse"></div>
              <span className="font-semibold text-red-600">LIVE CALL</span>
            </>
          ) : (
            <span className="font-semibold text-gray-500">No active call</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Users size={18} />
          <span className="font-semibold">{callStatus.participant_count}</span>
        </div>
      </div>

      {callStatus.is_live && (
        <div className="mb-4 max-h-48 overflow-y-auto">
          <h3 className="font-semibold mb-2">Participants:</h3>
          <ul className="space-y-2">
            {participants.map((participant) => (
              <li key={participant.user_id} className="text-sm bg-gray-50 p-2 rounded">
                <div className="font-medium">{participant.full_name}</div>
                <div className="text-gray-500 text-xs">@{participant.username}</div>
                <div className="text-gray-400 text-xs">
                  Joined: {new Date(participant.joined_at).toLocaleTimeString()}
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="flex gap-2">
        {!callStatus.is_live ? (
          <button
            onClick={handleStartCall}
            disabled={loading}
            className="flex-1 flex items-center justify-center gap-2 bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded-lg font-semibold disabled:opacity-50"
          >
            <Phone size={18} />
            Start Call
          </button>
        ) : !isInCall ? (
          <button
            onClick={handleJoinCall}
            disabled={loading}
            className="flex-1 flex items-center justify-center gap-2 bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-lg font-semibold disabled:opacity-50"
          >
            <Phone size={18} />
            Join Call
          </button>
        ) : (
          <button
            onClick={handleLeaveCall}
            disabled={loading}
            className="flex-1 flex items-center justify-center gap-2 bg-red-500 hover:bg-red-600 text-white px-4 py-2 rounded-lg font-semibold disabled:opacity-50"
          >
            <PhoneOff size={18} />
            Leave Call
          </button>
        )}
      </div>
    </div>
  );
}

export default EventCall;
```

---

## Testing with cURL

**Check Call Status:**
```bash
curl -X GET "http://localhost:8000/api/v1/messages/event_123/call/status" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Start a Call:**
```bash
curl -X POST "http://localhost:8000/api/v1/messages/event_123/call/start" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json"
```

**Join a Call:**
```bash
curl -X POST "http://localhost:8000/api/v1/messages/event_123/call/join" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json"
```

**Leave a Call:**
```bash
curl -X POST "http://localhost:8000/api/v1/messages/event_123/call/leave" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json"
```

**End a Call (initiator only):**
```bash
curl -X POST "http://localhost:8000/api/v1/messages/event_123/call/end" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json"
```

---

## Key Features

✅ **Multiple Participants** - Track all users currently in a call
✅ **Automatic Cleanup** - Call ends automatically when last person leaves
✅ **Initiator Control** - Only call starter can end the call
✅ **Real-time Status** - Fetch current participant count and list
✅ **Call Duration** - Track when call started with `started_at`
✅ **Join Tracking** - Know when each participant joined

---

## Best Practices

1. **Poll Status Regularly** - Check call status every 3-5 seconds
2. **Handle Errors** - Gracefully handle "no active call" errors
3. **Update UI** - Show live call indicator and participant list
4. **Participant Notifications** - Notify users when someone joins/leaves
5. **Audio/Video Setup** - Integrate with WebRTC (e.g., daily.co, Twilio)
6. **Network Optimization** - Use exponential backoff for retries

---

## Integration with WebRTC

This API tracks call state. For actual audio/video, integrate with:

- **Daily.co** - Easy-to-use video API
- **Twilio** - Enterprise video solution
- **Jitsi** - Open-source video platform

Example with Daily.co:
```javascript
import Daily from '@daily-co/daily-js';

async function setupCallWithDaily(eventId, accessToken) {
  // First, register with our backend
  const joinResponse = await fetch(`/api/v1/messages/${eventId}/call/join`, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${accessToken}` }
  });

  // Then start Daily.co call
  const callFrame = Daily.createFrame({
    showLeaveButton: true,
    showFullscreenButton: true
  });

  await callFrame.join({ url: dailyRoomUrl });
}
```

---

## Troubleshooting

**"No active call for this event"**
- Make sure someone started the call first
- Call may have ended if all participants left

**"Only the call initiator can end the call"**
- Ask the person who started the call to end it
- Or they can leave and the call auto-ends

**"A call is already active"**
- Join the existing call instead of starting a new one
- Check call status first to see if one exists

---

## Questions?

For API issues, refer to the backend team.
For frontend implementation, use the React component example above as a starting point.
