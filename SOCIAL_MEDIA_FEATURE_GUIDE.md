# Social Media Post Generation Feature

## Overview

After an event is created, the system automatically generates platform-optimized social media posts with trending hashtags. Users can review and provide feedback on the generated posts.

---

## Event Creation Flow with Social Media Posts

### Complete Workflow:

```
1. User starts event creation
2. System collects: name, description, place, date, time, type, participants, speakers
3. Event is created and saved to database
4. ✨ Social media posts are automatically generated
5. User reviews and provides feedback on posts
6. Posts and feedback are recorded in system
```

---

## Social Media Post Generation Features

### Automated Features:

✅ **Platform-Specific Optimization**
- Twitter: 280 characters, maximum engagement
- Instagram: 150 characters with emojis for visual appeal
- LinkedIn: 300 characters, professional tone

✅ **Trending Hashtags**
- Fetches latest hashtags from social media trends (via Xpoz MCP)
- Selects top 5 most relevant hashtags
- Falls back to category defaults if trends unavailable

✅ **Opik Integration**
- All post generations are tracked in Opik
- Hashtag selection is logged
- User feedback is recorded with metadata
- Thread ID correlates posts with conversations

### Generated Content Includes:

- Event name and key details
- Location and date
- Call-to-action for event attendance
- Trending and relevant hashtags
- Platform-specific formatting and emojis

---

## Frontend Integration Points

### 1. Displaying Generated Posts

After event creation completes, the SSE stream will send:

```json
{
  "event": "social_media_posts_generated",
  "posts": {
    "twitter": "Join us for an Eco-Friendly Recycling Initiative! 🌱 Learn sustainable practices at [location] on [date]. Limited spots available! #sustainability #ecofriendly #greeninitiative",
    "instagram": "♻️ Join our recycling event! Learn how to make a difference in your community. 🌍 [date] at [location] #sustainability",
    "linkedin": "We're hosting a community recycling initiative focused on sustainable practices. Join us to make an impact! #sustainability #community"
  },
  "hashtags": ["#sustainability", "#ecofriendly", "#greeninitiative", "#climateaction", "#community"],
  "session_id": "abc-123-def-456"
}
```

### 2. Displaying to User

Show the posts in a clean UI:

```jsx
<div className="social-media-posts">
  <div className="post-platform">
    <h3>🐦 Twitter</h3>
    <p className="post-text">{posts.twitter}</p>
    <span className="char-count">{posts.twitter.length}/280</span>
  </div>
  
  <div className="post-platform">
    <h3>📷 Instagram</h3>
    <p className="post-text">{posts.instagram}</p>
    <span className="char-count">{posts.instagram.length}/150</span>
  </div>
  
  <div className="post-platform">
    <h3>💼 LinkedIn</h3>
    <p className="post-text">{posts.linkedin}</p>
    <span className="char-count">{posts.linkedin.length}/300</span>
  </div>
</div>
```

### 3. Hashtags Display

```jsx
<div className="hashtags">
  <h4>Trending Hashtags Used:</h4>
  <div className="hashtag-list">
    {hashtags.map(tag => (
      <span key={tag} className="hashtag">{tag}</span>
    ))}
  </div>
</div>
```

---

## User Feedback on Posts

### Feedback Collection

After displaying posts, prompt for feedback:

```
"How do you feel about these posts? Any changes you'd like me to make?"
```

### Feedback Actions Users Can Take:

1. **Approve as-is**
   - User: "Looks great!"
   - System: Records approval and ends

2. **Request refinement**
   - User: "Make the Instagram post more fun"
   - System: Regenerates and shows new versions

3. **Modify specific platform**
   - User: "Can you make the Twitter version shorter and add more emojis?"
   - System: Refines requested posts

4. **Change hashtags**
   - User: "Use different hashtags that are more local"
   - System: Regenerates with new hashtag strategy

### Example User Flows:

**Flow 1: Direct Approval**
```
System: "Here are your social media posts..."
User: "Perfect! Let's use these"
Result: Posts stored, event ready for promotion
```

**Flow 2: Request Refinement**
```
System: "Here are your social media posts..."
User: "Make the Twitter post more engaging"
System: Regenerates Twitter post and displays
User: "Much better! ✅"
Result: Updated posts stored
```

---

## API Endpoints Involved

### POST /api/v1/stream (Chat Stream)

Returns SSE events including `social_media_posts_generated`:

```javascript
// Listen for social media posts event
eventSource.addEventListener('message', (event) => {
  const data = JSON.parse(event.data);
  
  if (data.event === 'social_media_posts_generated') {
    // Display posts and collect feedback
    displaySocialMediaPosts(data.posts, data.hashtags);
  }
});
```

### Continue Stream with Feedback

When user provides feedback, send as a new message in the same thread:

```javascript
// User has reviewed posts and provided feedback
const feedbackMessage = {
  "message": "The Instagram post needs more emojis and energy",
  "thread_id": "abc-123-def-456"  // Same thread
};

// Send to /api/v1/stream
fetch('/api/v1/stream', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(feedbackMessage)
})
```

---

## Complete React Implementation

```jsx
import React, { useState, useEffect } from 'react';
import { Copy, Share2, RefreshCw } from 'lucide-react';

function SocialMediaPostGenerator({ sessionId, threadId, accessToken }) {
  const [posts, setPosts] = useState(null);
  const [hashtags, setHashtags] = useState([]);
  const [loading, setLoading] = useState(false);
  const [feedbackInput, setFeedbackInput] = useState('');
  const [showFeedback, setShowFeedback] = useState(false);
  const [copiedPlatform, setCopiedPlatform] = useState(null);

  const copyToClipboard = (text, platform) => {
    navigator.clipboard.writeText(text);
    setCopiedPlatform(platform);
    setTimeout(() => setCopiedPlatform(null), 2000);
  };

  const handleSubmitFeedback = async () => {
    if (!feedbackInput.trim()) return;

    setLoading(true);
    try {
      // Send feedback as a message in the same thread
      const eventSource = new EventSource(
        `/api/v1/stream?message=${encodeURIComponent(feedbackInput)}&thread_id=${threadId}`,
        {
          headers: {
            'Authorization': `Bearer ${accessToken}`
          }
        }
      );

      eventSource.addEventListener('message', (event) => {
        const data = JSON.parse(event.data);
        
        if (data.event === 'social_media_posts_generated') {
          setPosts(data.posts);
          setHashtags(data.hashtags);
          setFeedbackInput('');
          setShowFeedback(false);
        }
        
        if (data.event === 'end') {
          eventSource.close();
          setLoading(false);
        }
      });

      eventSource.onerror = () => {
        eventSource.close();
        setLoading(false);
      };
    } catch (error) {
      console.error('Error submitting feedback:', error);
      setLoading(false);
    }
  };

  if (!posts) return <div>No posts generated yet</div>;

  return (
    <div className="social-media-container">
      <div className="posts-grid">
        {/* Twitter Post */}
        <div className="post-card twitter">
          <div className="post-header">
            <h3>🐦 Twitter</h3>
            <span className="char-count">{posts.twitter.length}/280</span>
          </div>
          <p className="post-content">{posts.twitter}</p>
          <div className="post-actions">
            <button 
              onClick={() => copyToClipboard(posts.twitter, 'twitter')}
              className="btn-copy"
            >
              <Copy size={16} />
              {copiedPlatform === 'twitter' ? 'Copied!' : 'Copy'}
            </button>
            <button className="btn-share">
              <Share2 size={16} />
              Share
            </button>
          </div>
        </div>

        {/* Instagram Post */}
        <div className="post-card instagram">
          <div className="post-header">
            <h3>📷 Instagram</h3>
            <span className="char-count">{posts.instagram.length}/150</span>
          </div>
          <p className="post-content">{posts.instagram}</p>
          <div className="post-actions">
            <button 
              onClick={() => copyToClipboard(posts.instagram, 'instagram')}
              className="btn-copy"
            >
              <Copy size={16} />
              {copiedPlatform === 'instagram' ? 'Copied!' : 'Copy'}
            </button>
            <button className="btn-share">
              <Share2 size={16} />
              Share
            </button>
          </div>
        </div>

        {/* LinkedIn Post */}
        <div className="post-card linkedin">
          <div className="post-header">
            <h3>💼 LinkedIn</h3>
            <span className="char-count">{posts.linkedin.length}/300</span>
          </div>
          <p className="post-content">{posts.linkedin}</p>
          <div className="post-actions">
            <button 
              onClick={() => copyToClipboard(posts.linkedin, 'linkedin')}
              className="btn-copy"
            >
              <Copy size={16} />
              {copiedPlatform === 'linkedin' ? 'Copied!' : 'Copy'}
            </button>
            <button className="btn-share">
              <Share2 size={16} />
              Share
            </button>
          </div>
        </div>
      </div>

      {/* Hashtags */}
      <div className="hashtags-section">
        <h4>📌 Trending Hashtags</h4>
        <div className="hashtag-list">
          {hashtags.map(tag => (
            <span 
              key={tag} 
              className="hashtag"
              onClick={() => copyToClipboard(tag, 'hashtag')}
            >
              {tag}
            </span>
          ))}
        </div>
      </div>

      {/* Feedback Section */}
      <div className="feedback-section">
        {!showFeedback ? (
          <div className="feedback-prompt">
            <p>How do you feel about these posts?</p>
            <div className="feedback-actions">
              <button 
                onClick={() => setShowFeedback(true)}
                className="btn-feedback"
              >
                <RefreshCw size={16} />
                Refine Posts
              </button>
              <button className="btn-approve">
                ✓ Approve & Use
              </button>
            </div>
          </div>
        ) : (
          <div className="feedback-input">
            <textarea
              placeholder="Tell me what you'd like to change (e.g., 'Make Instagram post more fun', 'Add more emojis', 'Focus on sustainability')..."
              value={feedbackInput}
              onChange={(e) => setFeedbackInput(e.target.value)}
              disabled={loading}
              rows={3}
            />
            <div className="feedback-actions">
              <button 
                onClick={handleSubmitFeedback}
                disabled={loading || !feedbackInput.trim()}
                className="btn-submit"
              >
                {loading ? 'Refining...' : 'Refine Posts'}
              </button>
              <button 
                onClick={() => setShowFeedback(false)}
                className="btn-cancel"
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default SocialMediaPostGenerator;
```

---

## Styling Example (Tailwind CSS)

```jsx
const styles = `
  .social-media-container {
    padding: 24px;
    background: white;
    border-radius: 12px;
  }

  .posts-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 20px;
    margin-bottom: 30px;
  }

  .post-card {
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 16px;
    background: #f9fafb;
  }

  .post-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
  }

  .char-count {
    font-size: 12px;
    color: #9ca3af;
  }

  .post-content {
    line-height: 1.6;
    margin-bottom: 12px;
    white-space: pre-wrap;
  }

  .post-actions {
    display: flex;
    gap: 8px;
  }

  .btn-copy, .btn-share {
    flex: 1;
    padding: 8px;
    font-size: 12px;
    border: 1px solid #d1d5db;
    border-radius: 4px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 4px;
  }

  .hashtags-section {
    margin-bottom: 20px;
  }

  .hashtag-list {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 8px;
  }

  .hashtag {
    padding: 4px 12px;
    background: #dbeafe;
    color: #0369a1;
    border-radius: 20px;
    font-size: 12px;
    cursor: pointer;
  }

  .feedback-section {
    border-top: 1px solid #e5e7eb;
    padding-top: 20px;
  }

  .feedback-prompt, .feedback-input {
    text-align: center;
  }

  textarea {
    width: 100%;
    padding: 12px;
    border: 1px solid #d1d5db;
    border-radius: 8px;
    font-family: inherit;
    resize: vertical;
  }
`;
```

---

## Opik Tracking Details

### What Gets Tracked:

1. **Post Generation**
   - Event name and details
   - All three post versions
   - Hashtags used
   - Generation timestamp

2. **User Feedback**
   - Feedback content
   - Thread ID for correlation
   - Feedback timestamp
   - Platform-specific changes requested

3. **Metadata Stored**
   - User ID
   - Session ID
   - Thread ID
   - Event type and category

### Accessing in Opik Dashboard:

Search for traces with tags:
- `social_media_post_generated`
- `user_feedback`
- Post platform: `twitter`, `instagram`, `linkedin`

---

## Error Handling

### Hashtag Fetch Fails
- Automatically falls back to category-based hashtags
- Posts still generated successfully
- User notified: "Using popular hashtags for this category"

### Post Generation Error
- System retries once
- If failed: Show generic template posts
- Notify user: "Posts generated with default format"

### Feedback Processing Error
- Display error message: "Failed to process feedback"
- Allow user to retry or skip
- Continue event flow

---

## Testing Checklist

- [ ] Posts display correctly on all screen sizes
- [ ] Character counts update as text changes
- [ ] Copy-to-clipboard works for posts and hashtags
- [ ] Feedback input focuses when "Refine Posts" clicked
- [ ] Loading states show during refinement
- [ ] Error handling displays properly
- [ ] Hashtag fetching works/falls back correctly
- [ ] Posts are platform-appropriate in length
- [ ] Emojis display correctly on all platforms
- [ ] Mobile responsive design works

---

## Questions?

For backend integration or feature questions, contact the backend team.
For UI/UX improvements, discuss with the frontend team lead.
