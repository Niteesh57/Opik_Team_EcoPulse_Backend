# Frontend Integration Guide: User Feedback API

## Overview
This guide explains how to integrate the user feedback feature into the frontend chat interface. The feedback API allows users to like/dislike AI responses, which helps improve the system and tracks user satisfaction in Opik.

---

## API Endpoint

### Update Message Feedback
**Endpoint:** `PATCH /api/v1/messages/{message_id}/feedback`

**Authentication:** Required (Bearer Token)

**Headers:**
```http
Authorization: Bearer <your_access_token>
Content-Type: application/json
```

---

## Request Format

### Path Parameters
- `message_id` (integer, required): The ID of the message to provide feedback on

### Request Body
```json
{
  "liked": true,      // Optional: Set to true if user likes the message
  "disliked": false   // Optional: Set to true if user dislikes the message
}
```

**Important Rules:**
- You cannot set both `liked` and `disliked` to `true` simultaneously
- To remove feedback, send both as `false` or `null`
- Only one field needs to be set to provide feedback

---

## Response Format

### Success Response (200 OK)
```json
{
  "id": 123,
  "session_id": "abc-123-def-456",
  "role": "assistant",
  "user_id": 1,
  "user_message": null,
  "ai_message": "Here's my response to your question...",
  "liked": true,
  "disliked": false,
  "created_at": "2026-02-02T10:30:00",
  "updated_at": "2026-02-02T10:35:00"
}
```

### Error Responses

#### 400 Bad Request
```json
{
  "detail": "Message cannot be liked and disliked simultaneously"
}
```

#### 404 Not Found
```json
{
  "detail": "Message not found"
}
```

#### 401 Unauthorized
```json
{
  "detail": "Not authenticated"
}
```

---

## Complete Workflow: Chat with Feedback

### Step 1: Start a Chat Session

**POST** `/api/v1/stream`
```json
{
  "message": "Hello, can you help me create a recycling event?",
  "thread_id": null  // null for new session, or existing thread_id to continue
}
```

**Response (Server-Sent Events):**
```
data: {"event":"session","session_id":"abc-123","message_id":456,"thread_id":"abc-123","created_session":true}

data: {"event":"status","status":"reasoning","message":"Analyzing your request..."}

data: {"delta":"Sure! I'd be happy to help you create a recycling event."}

data: {"delta":" Let me gather some information..."}

data: {"event":"end","session_id":"abc-123","message_id":456,"assistant_message_id":457}
```

### Step 2: Extract Message IDs

From the SSE stream, capture:
- `message_id`: The user's message ID (456 in example)
- `assistant_message_id`: The AI's response message ID (457 in example)

### Step 3: Display Feedback UI

Show thumbs up/down buttons next to the AI message. When user clicks:

**User Likes the Response:**
```javascript
fetch('/api/v1/messages/457/feedback', {
  method: 'PATCH',
  headers: {
    'Authorization': `Bearer ${accessToken}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    liked: true,
    disliked: false
  })
})
.then(response => response.json())
.then(data => {
  console.log('Feedback submitted:', data);
  // Update UI to show thumbs up is active
})
.catch(error => {
  console.error('Error submitting feedback:', error);
});
```

**User Dislikes the Response:**
```javascript
fetch('/api/v1/messages/457/feedback', {
  method: 'PATCH',
  headers: {
    'Authorization': `Bearer ${accessToken}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    liked: false,
    disliked: true
  })
})
.then(response => response.json())
.then(data => {
  console.log('Feedback submitted:', data);
  // Update UI to show thumbs down is active
});
```

**User Removes Feedback:**
```javascript
fetch('/api/v1/messages/457/feedback', {
  method: 'PATCH',
  headers: {
    'Authorization': `Bearer ${accessToken}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    liked: null,
    disliked: null
  })
})
```

---

## React Example Implementation

```jsx
import React, { useState } from 'react';
import { ThumbsUp, ThumbsDown } from 'lucide-react';

function MessageFeedback({ messageId, initialLiked, initialDisliked, accessToken }) {
  const [liked, setLiked] = useState(initialLiked);
  const [disliked, setDisliked] = useState(initialDisliked);
  const [loading, setLoading] = useState(false);

  const submitFeedback = async (isLiked) => {
    setLoading(true);
    
    try {
      const response = await fetch(`/api/v1/messages/${messageId}/feedback`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          liked: isLiked ? true : null,
          disliked: !isLiked ? true : null
        })
      });

      if (!response.ok) {
        throw new Error('Failed to submit feedback');
      }

      const data = await response.json();
      setLiked(data.liked);
      setDisliked(data.disliked);
      
      // Optional: Show success toast
      console.log('Feedback submitted successfully');
      
    } catch (error) {
      console.error('Error submitting feedback:', error);
      // Optional: Show error toast
    } finally {
      setLoading(false);
    }
  };

  const handleLike = () => {
    if (liked) {
      // Remove like
      submitFeedback(null);
    } else {
      // Set like
      submitFeedback(true);
    }
  };

  const handleDislike = () => {
    if (disliked) {
      // Remove dislike
      submitFeedback(null);
    } else {
      // Set dislike
      submitFeedback(false);
    }
  };

  return (
    <div className="flex gap-2 mt-2">
      <button
        onClick={handleLike}
        disabled={loading}
        className={`p-2 rounded-full transition-colors ${
          liked 
            ? 'bg-green-100 text-green-600' 
            : 'hover:bg-gray-100 text-gray-400'
        }`}
        aria-label="Like this response"
      >
        <ThumbsUp size={16} fill={liked ? 'currentColor' : 'none'} />
      </button>
      
      <button
        onClick={handleDislike}
        disabled={loading}
        className={`p-2 rounded-full transition-colors ${
          disliked 
            ? 'bg-red-100 text-red-600' 
            : 'hover:bg-gray-100 text-gray-400'
        }`}
        aria-label="Dislike this response"
      >
        <ThumbsDown size={16} fill={disliked ? 'currentColor' : 'none'} />
      </button>
    </div>
  );
}

export default MessageFeedback;
```

---

## Loading Existing Messages with Feedback

When loading chat history, use:

**GET** `/api/v1/sessions/{session_id}/messages`

**Response:**
```json
[
  {
    "id": 456,
    "role": "user",
    "user_message": "Hello, can you help me?",
    "ai_message": null,
    "liked": null,
    "disliked": null,
    "created_at": "2026-02-02T10:30:00"
  },
  {
    "id": 457,
    "role": "assistant",
    "user_message": null,
    "ai_message": "Of course! How can I assist you?",
    "liked": true,          // User previously liked this
    "disliked": false,
    "created_at": "2026-02-02T10:30:05"
  }
]
```

Use the `liked` and `disliked` fields to render the feedback UI in the correct state.

---

## Best Practices

### 1. **Debounce Feedback Submissions**
Prevent accidental double-clicks:
```javascript
const debouncedSubmit = debounce(submitFeedback, 500);
```

### 2. **Show Loading States**
Disable buttons while feedback is being submitted

### 3. **Optimistic UI Updates**
Update the UI immediately, then revert if the API call fails

### 4. **Handle Errors Gracefully**
```javascript
try {
  await submitFeedback(isLiked);
} catch (error) {
  // Show toast: "Failed to submit feedback. Please try again."
  // Revert UI to previous state
}
```

### 5. **Store Message IDs**
When processing SSE events, store the `assistant_message_id` with each AI message in your UI state

### 6. **Accessibility**
- Add proper ARIA labels
- Ensure keyboard navigation works
- Provide visual feedback for active states

---

## Testing the API

### Using cURL

**Submit Like:**
```bash
curl -X PATCH "http://localhost:8000/api/v1/messages/457/feedback" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"liked": true, "disliked": false}'
```

**Submit Dislike:**
```bash
curl -X PATCH "http://localhost:8000/api/v1/messages/457/feedback" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"liked": false, "disliked": true}'
```

**Remove Feedback:**
```bash
curl -X PATCH "http://localhost:8000/api/v1/messages/457/feedback" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"liked": null, "disliked": null}'
```

### Using Postman

1. Set method to `PATCH`
2. URL: `http://localhost:8000/api/v1/messages/{message_id}/feedback`
3. Headers:
   - `Authorization: Bearer <token>`
   - `Content-Type: application/json`
4. Body (raw JSON):
   ```json
   {
     "liked": true,
     "disliked": false
   }
   ```

---

## Backend Integration (What Happens Behind the Scenes)

When feedback is submitted, the backend:

1. ✅ **Validates** the request (only user who owns the message can provide feedback)
2. ✅ **Updates** the database with the feedback
3. ✅ **Sends to Opik** for analytics and AI improvement tracking
4. ✅ **Returns** the updated message object

The Opik integration tracks:
- Thread ID (for conversation context)
- User ID
- Message ID
- Feedback score (1.0 for like, 0.0 for dislike)
- Timestamp

---

## Troubleshooting

### Issue: "Message not found"
- Verify the `message_id` is correct
- Ensure the user is authenticated as the message owner

### Issue: "Cannot like and dislike simultaneously"
- Only set one field to `true` at a time
- To toggle, set the opposite field to `true`

### Issue: Feedback not updating in UI
- Check the response from the API
- Verify you're updating state with the returned `liked`/`disliked` values

---

## Additional Endpoints

### Get Session Messages
**GET** `/api/v1/sessions/{session_id}/messages`

Returns all messages in a session, including feedback status.

### Get Single Message
**GET** `/api/v1/messages/{message_id}`

Returns a single message with current feedback status.

---

## Questions?

For backend issues or API changes, contact the backend team.
For frontend implementation help, refer to this guide or the React example above.

**Base URL (Development):** `http://localhost:8000`
**Base URL (Production):** `https://your-domain.com`
