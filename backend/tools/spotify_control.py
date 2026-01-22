#!/usr/bin/env python3
"""
Spotify Control Tool
Controls Spotify playback and manages playlists via Web API
"""

import os
import json
import time
import urllib.request
import urllib.parse
import urllib.error
from typing import Optional, Dict, Any, List

# =============================================================================
# CONFIGURATION
# =============================================================================

SPOTIFY_API_BASE = "https://api.spotify.com/v1"

# Spotify credentials from environment
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REFRESH_TOKEN = os.getenv("SPOTIFY_REFRESH_TOKEN")

# In-memory token cache for session persistence
_token_cache = {
    "access_token": None,
    "expires_at": 0
}

# =============================================================================
# AUTHENTICATION
# =============================================================================

def load_spotify_config() -> Dict[str, Any]:
    """Load Spotify configuration"""
    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET or not SPOTIFY_REFRESH_TOKEN:
        raise Exception("Missing Spotify credentials!")
    
    return {
        "clientId": SPOTIFY_CLIENT_ID,
        "clientSecret": SPOTIFY_CLIENT_SECRET,
        "refreshToken": SPOTIFY_REFRESH_TOKEN,
        "accessToken": _token_cache["access_token"],
        "expiresAt": _token_cache["expires_at"]
    }


def save_spotify_config(config: Dict[str, Any]) -> None:
    """Save updated tokens to in-memory cache"""
    _token_cache["access_token"] = config.get("accessToken")
    _token_cache["expires_at"] = config.get("expiresAt", 0)


def refresh_access_token(config: Dict[str, Any]) -> str:
    """Refresh the Spotify access token using refresh token"""
    data = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": config["refreshToken"],
        "client_id": config["clientId"],
        "client_secret": config["clientSecret"],
    }).encode('utf-8')
    
    req = urllib.request.Request(
        "https://accounts.spotify.com/api/token",
        data=data,
        method='POST'
    )
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            response_data = json.loads(response.read().decode('utf-8'))
            config["accessToken"] = response_data["access_token"]
            config["expiresAt"] = int(time.time() * 1000) + (response_data["expires_in"] * 1000)
            save_spotify_config(config)
            return response_data["access_token"]
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        raise Exception(f"Failed to refresh token: {error_body}")


def get_access_token() -> str:
    """Get valid access token, refreshing if necessary"""
    config = load_spotify_config()
    
    # Check if token is expired (with 60s buffer)
    current_time = int(time.time() * 1000)
    expires_at = config.get("expiresAt", 0)
    
    if current_time >= (expires_at - 60000):
        return refresh_access_token(config)
    
    return config["accessToken"]


def make_spotify_request(
    method: str,
    endpoint: str,
    data: Optional[Dict] = None,
    params: Optional[Dict] = None
) -> Dict[str, Any]:
    """Make authenticated request to Spotify API"""
    token = get_access_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    url = f"{SPOTIFY_API_BASE}{endpoint}"
    
    # Add query params to URL if provided
    if params:
        url += "?" + urllib.parse.urlencode(params)
    
    # Prepare request data
    request_data = None
    if data:
        request_data = json.dumps(data).encode('utf-8')
    
    req = urllib.request.Request(url, data=request_data, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            # 204 No Content = success (common for POST/PUT with no return data)
            if response.status == 204:
                return {"success": True}
            
            # 200 OK with potential body
            response_body = response.read().decode('utf-8').strip()
            if response_body:
                try:
                    return json.loads(response_body)
                except json.JSONDecodeError:
                    # Empty or invalid JSON but status was OK = success
                    return {"success": True}
            return {"success": True}
            
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        try:
            error_json = json.loads(error_body)
            error_msg = error_json.get("error", {}).get("message", error_body)
        except:
            error_msg = error_body
        return {"success": False, "error": error_msg, "status": e.code}


# =============================================================================
# SPOTIFY CONTROL FUNCTIONS
# =============================================================================

def search_spotify(
    query: str,
    search_type: str = "track",
    limit: int = 10,
    return_raw: bool = False
) -> Any:
    """
    Search for tracks, artists, albums, or playlists on Spotify
    
    Args:
        query: Search term
        search_type: One of: track, artist, album, playlist
        limit: Number of results (1-50)
        return_raw: If True, return raw response dict instead of formatted string
    
    Returns:
        Formatted search results (str) or raw response (dict) if return_raw=True
    """
    if limit < 1 or limit > 50:
        limit = 10
    
    response = make_spotify_request(
        "GET",
        "/search",
        params={
            "q": query,
            "type": search_type,
            "limit": limit
        }
    )
    
    if not response.get("success", True):
        if return_raw:
            return {"success": False, "error": response.get('error', 'Unknown error')}
        return f"❌ Search failed: {response.get('error', 'Unknown error')}"
    
    # If raw response requested, return it for programmatic use
    if return_raw:
        return response
    
    # Otherwise format for human-readable output
    results = []
    
    if search_type == "track":
        items = response.get("tracks", {}).get("items", [])
        for item in items:
            artists = ", ".join([a["name"] for a in item["artists"]])
            results.append(f"🎵 {item['name']} - {artists} (ID: {item['id']})")
    
    elif search_type == "artist":
        items = response.get("artists", {}).get("items", [])
        for item in items:
            results.append(f"🎤 {item['name']} (ID: {item['id']})")
    
    elif search_type == "album":
        items = response.get("albums", {}).get("items", [])
        for item in items:
            artists = ", ".join([a["name"] for a in item["artists"]])
            results.append(f"💿 {item['name']} - {artists} (ID: {item['id']})")
    
    elif search_type == "playlist":
        items = response.get("playlists", {}).get("items", [])
        for item in items:
            results.append(f"📋 {item['name']} by {item['owner']['display_name']} (ID: {item['id']})")
    
    if not results:
        return f"🔍 No {search_type}s found for: {query}"
    
    return f"🔍 Found {len(results)} {search_type}(s) for '{query}':\n\n" + "\n".join(results)


def play_music(
    spotify_id: Optional[str] = None,
    content_type: str = "track",
    query: Optional[str] = None
) -> str:
    """
    Play a track, album, artist, or playlist
    
    Args:
        spotify_id: Spotify ID of the content (if not provided, query must be provided)
        content_type: One of: track, album, artist, playlist
        query: Search query (alternative to spotify_id - will play first result)
    
    Returns:
        Success/error message
    """
    # If no spotify_id provided, search for it
    if not spotify_id:
        if not query:
            return "❌ Either spotify_id or query must be provided"
        
        # Search for the content
        search_response = search_spotify(query, content_type, limit=1, return_raw=True)
        
        if not search_response.get("success", True) or "error" in search_response:
            return f"❌ Search failed: {search_response.get('error', 'No results found')}"
        
        # Extract first result
        items_key = f"{content_type}s"
        items = search_response.get(items_key, {}).get("items", [])
        
        if not items:
            return f"🔍 No {content_type}s found for: {query}"
        
        first_item = items[0]
        spotify_id = first_item["id"]
        
        # Get name for user feedback
        item_name = first_item.get("name", "Unknown")
        if content_type == "track":
            artists = ", ".join([a["name"] for a in first_item.get("artists", [])])
            item_display = f"{item_name} - {artists}"
        else:
            item_display = item_name
    else:
        item_display = spotify_id
    
    uri = f"spotify:{content_type}:{spotify_id}"
    
    # Different payload structure for tracks vs context
    if content_type == "track":
        payload = {"uris": [uri]}
    else:
        payload = {"context_uri": uri}
    
    response = make_spotify_request("PUT", "/me/player/play", data=payload)
    
    if response.get("success"):
        if query:
            return f"▶️ Now playing: {item_display}\n(Found via search: '{query}')"
        return f"▶️ Now playing {content_type}: {item_display}"
    else:
        error = response.get("error", "Unknown error")
        # Check if no active device
        if response.get("status") == 404:
            return "⚠️ No active Spotify device found. Please open Spotify on a device and try again."
        return f"❌ Failed to play: {error}"


def pause_playback() -> str:
    """Pause current playback"""
    response = make_spotify_request("PUT", "/me/player/pause")
    
    if response.get("success"):
        return "⏸️ Playback paused"
    else:
        return f"❌ Failed to pause: {response.get('error', 'Unknown error')}"


def skip_to_next() -> str:
    """Skip to next track"""
    response = make_spotify_request("POST", "/me/player/next")
    
    if response.get("success"):
        return "⏭️ Skipped to next track"
    else:
        return f"❌ Failed to skip: {response.get('error', 'Unknown error')}"


def skip_to_previous() -> str:
    """Skip to previous track"""
    response = make_spotify_request("POST", "/me/player/previous")
    
    if response.get("success"):
        return "⏮️ Skipped to previous track"
    else:
        return f"❌ Failed to skip: {response.get('error', 'Unknown error')}"


def get_now_playing() -> str:
    """Get currently playing track information"""
    response = make_spotify_request("GET", "/me/player/currently-playing")
    
    if not response.get("success", True):
        return f"❌ Failed to get current track: {response.get('error', 'Unknown error')}"
    
    if not response or not response.get("item"):
        return "🔇 Nothing currently playing"
    
    item = response["item"]
    is_playing = response.get("is_playing", False)
    progress_ms = response.get("progress_ms", 0)
    duration_ms = item.get("duration_ms", 0)
    
    artists = ", ".join([a["name"] for a in item["artists"]])
    track_name = item["name"]
    album_name = item["album"]["name"]
    
    # Convert milliseconds to minutes:seconds
    progress_min = progress_ms // 60000
    progress_sec = (progress_ms % 60000) // 1000
    duration_min = duration_ms // 60000
    duration_sec = (duration_ms % 60000) // 1000
    
    status = "▶️" if is_playing else "⏸️"
    
    return f"""{status} Now Playing:
🎵 {track_name}
🎤 {artists}
💿 {album_name}
⏱️ {progress_min}:{progress_sec:02d} / {duration_min}:{duration_sec:02d}
🆔 Track ID: {item['id']}"""


def create_playlist(
    name: str,
    description: str = "",
    public: bool = False
) -> str:
    """
    Create a new Spotify playlist
    
    Args:
        name: Playlist name
        description: Playlist description
        public: Whether playlist is public
    
    Returns:
        Playlist ID and URL
    """
    # Get current user ID
    user_response = make_spotify_request("GET", "/me")
    if not user_response.get("success", True):
        return f"❌ Failed to get user info: {user_response.get('error', 'Unknown error')}"
    
    user_id = user_response["id"]
    
    # Create playlist
    response = make_spotify_request(
        "POST",
        f"/users/{user_id}/playlists",
        data={
            "name": name,
            "description": description,
            "public": public
        }
    )
    
    if response.get("success") == False:
        return f"❌ Failed to create playlist: {response.get('error', 'Unknown error')}"
    
    playlist_id = response["id"]
    playlist_url = response["external_urls"]["spotify"]
    
    return f"""✅ Created playlist: {name}
🆔 ID: {playlist_id}
🔗 URL: {playlist_url}"""


def add_tracks_to_playlist(
    playlist_id: str,
    track_ids: Optional[List[str]] = None,
    query: Optional[str] = None
) -> str:
    """
    Add tracks to a playlist
    
    Args:
        playlist_id: Spotify playlist ID
        track_ids: List of Spotify track IDs (if not provided, query must be provided)
        query: Search query (alternative to track_ids - will add first result)
               Can be multiple queries separated by semicolons (;) to add multiple tracks
               Example: "bohemian rhapsody; stairway to heaven; hotel california"
    
    Returns:
        Success/error message
    """
    # If no track_ids provided, search for it
    if not track_ids:
        if not query:
            return "❌ Either track_ids or query must be provided"
        
        # Split query by semicolon for multiple tracks
        queries = [q.strip() for q in query.split(";") if q.strip()]
        
        track_ids = []
        found_tracks = []
        failed_searches = []
        
        # Search for each query
        for search_query in queries:
            search_response = search_spotify(search_query, "track", limit=1, return_raw=True)
            
            if not search_response.get("success", True) or "error" in search_response:
                failed_searches.append(f"'{search_query}': {search_response.get('error', 'No results')}")
                continue
            
            # Extract first result
            items = search_response.get("tracks", {}).get("items", [])
            
            if not items:
                failed_searches.append(f"'{search_query}': No tracks found")
                continue
            
            first_track = items[0]
            track_ids.append(first_track["id"])
            
            # Get track info for user feedback
            track_name = first_track.get("name", "Unknown")
            artists = ", ".join([a["name"] for a in first_track.get("artists", [])])
            found_tracks.append(f"🎵 {track_name} - {artists}")
        
        if not track_ids:
            return f"❌ No tracks found for any query:\n" + "\n".join(failed_searches)
        
        searched = True
    else:
        found_tracks = []
        failed_searches = []
        searched = False
    
    # Convert track IDs to URIs
    track_uris = [f"spotify:track:{tid}" for tid in track_ids]
    
    response = make_spotify_request(
        "POST",
        f"/playlists/{playlist_id}/tracks",
        data={"uris": track_uris}
    )
    
    if response.get("success") == False:
        return f"❌ Failed to add tracks: {response.get('error', 'Unknown error')}"
    
    if searched:
        result = f"✅ Added {len(track_ids)} track(s) to playlist:\n\n" + "\n".join(found_tracks)
        if failed_searches:
            result += f"\n\n⚠️ Failed to find {len(failed_searches)} track(s):\n" + "\n".join(failed_searches)
        return result
    
    return f"✅ Added {len(track_ids)} track(s) to playlist {playlist_id}"


def create_and_populate_playlist(
    name: str,
    songs: str,
    description: str = "",
    public: bool = False
) -> str:
    """
    Create a new playlist AND populate it with songs in ONE action!
    MASSIVE convenience - combines create_playlist + add_tracks_to_playlist
    
    Args:
        name: Playlist name
        songs: Semicolon-separated song queries
               Example: "bohemian rhapsody queen; stairway to heaven; hotel california"
        description: Playlist description (optional)
        public: Whether playlist is public (default False)
    
    Returns:
        Combined success/error message with playlist info and added tracks
    """
    # Step 1: Create the playlist
    user_response = make_spotify_request("GET", "/me")
    if not user_response.get("success", True):
        return f"❌ Failed to get user info: {user_response.get('error', 'Unknown error')}"
    
    user_id = user_response["id"]
    
    create_response = make_spotify_request(
        "POST",
        f"/users/{user_id}/playlists",
        data={
            "name": name,
            "description": description,
            "public": public
        }
    )
    
    if create_response.get("success") == False:
        return f"❌ Failed to create playlist: {create_response.get('error', 'Unknown error')}"
    
    playlist_id = create_response["id"]
    playlist_url = create_response["external_urls"]["spotify"]
    
    # Step 2: Search for and add songs
    queries = [q.strip() for q in songs.split(";") if q.strip()]
    
    if not queries:
        return f"""✅ Created empty playlist: {name}
🆔 ID: {playlist_id}
🔗 URL: {playlist_url}

⚠️ No songs provided to add"""
    
    track_ids = []
    found_tracks = []
    failed_searches = []
    
    # Search for each song
    for search_query in queries:
        search_response = search_spotify(search_query, "track", limit=1, return_raw=True)
        
        if not search_response.get("success", True) or "error" in search_response:
            failed_searches.append(f"'{search_query}': {search_response.get('error', 'No results')}")
            continue
        
        items = search_response.get("tracks", {}).get("items", [])
        
        if not items:
            failed_searches.append(f"'{search_query}': No tracks found")
            continue
        
        first_track = items[0]
        track_ids.append(first_track["id"])
        
        track_name = first_track.get("name", "Unknown")
        artists = ", ".join([a["name"] for a in first_track.get("artists", [])])
        found_tracks.append(f"🎵 {track_name} - {artists}")
    
    # Step 3: Add found tracks to the new playlist
    if track_ids:
        track_uris = [f"spotify:track:{tid}" for tid in track_ids]
        
        add_response = make_spotify_request(
            "POST",
            f"/playlists/{playlist_id}/tracks",
            data={"uris": track_uris}
        )
        
        if add_response.get("success") == False:
            return f"""✅ Created playlist: {name}
🆔 ID: {playlist_id}
🔗 URL: {playlist_url}

❌ But failed to add tracks: {add_response.get('error', 'Unknown error')}"""
    
    # Step 4: Build comprehensive result message
    result = f"""✅ Created & populated playlist: {name}
🆔 ID: {playlist_id}
🔗 URL: {playlist_url}

🎵 Added {len(track_ids)} track(s):
"""
    result += "\n".join(found_tracks)
    
    if failed_searches:
        result += f"\n\n⚠️ Failed to find {len(failed_searches)} track(s):\n"
        result += "\n".join(failed_searches)
    
    return result


def get_my_playlists(limit: int = 20) -> str:
    """
    Get user's playlists
    
    Args:
        limit: Number of playlists to return (1-50)
    
    Returns:
        Formatted list of playlists
    """
    if limit < 1 or limit > 50:
        limit = 20
    
    response = make_spotify_request(
        "GET",
        "/me/playlists",
        params={"limit": limit}
    )
    
    if not response.get("success", True):
        return f"❌ Failed to get playlists: {response.get('error', 'Unknown error')}"
    
    items = response.get("items", [])
    
    if not items:
        return "📋 You have no playlists"
    
    results = [f"📋 Your Playlists ({len(items)}):\n"]
    
    for item in items:
        track_count = item["tracks"]["total"]
        results.append(f"• {item['name']} ({track_count} tracks) - ID: {item['id']}")
    
    return "\n".join(results)


def add_to_queue(
    spotify_id: Optional[str] = None,
    content_type: str = "track",
    query: Optional[str] = None
) -> str:
    """
    Add track(s) to the playback queue
    
    Args:
        spotify_id: Spotify ID of the track to add (if not provided, query must be provided)
        content_type: Type of content (only "track" supported for queue)
        query: Search query (alternative to spotify_id - will queue first result)
               Can be multiple queries separated by semicolons (;) to add multiple tracks
               Example: "bohemian rhapsody; stairway to heaven; hotel california"
    
    Returns:
        Success/error message
    """
    if content_type != "track":
        return "⚠️ Only tracks can be added to queue. Use 'play' action for albums/playlists."
    
    # If no spotify_id provided, search for it
    if not spotify_id:
        if not query:
            return "❌ Either spotify_id or query must be provided"
        
        # Split query by semicolon for multiple tracks
        queries = [q.strip() for q in query.split(";") if q.strip()]
        
        track_ids = []
        found_tracks = []
        failed_searches = []
        
        # Search for each query
        for search_query in queries:
            search_response = search_spotify(search_query, "track", limit=1, return_raw=True)
            
            if not search_response.get("success", True) or "error" in search_response:
                failed_searches.append(f"'{search_query}': {search_response.get('error', 'No results')}")
                continue
            
            # Extract first result
            items = search_response.get("tracks", {}).get("items", [])
            
            if not items:
                failed_searches.append(f"'{search_query}': No tracks found")
                continue
            
            first_track = items[0]
            track_ids.append(first_track["id"])
            
            # Get track info for user feedback
            track_name = first_track.get("name", "Unknown")
            artists = ", ".join([a["name"] for a in first_track.get("artists", [])])
            found_tracks.append(f"🎵 {track_name} - {artists}")
        
        if not track_ids:
            return f"❌ No tracks found for any query:\n" + "\n".join(failed_searches)
        
        # Add all tracks to queue
        added_count = 0
        queue_errors = []
        
        for track_id, track_info in zip(track_ids, found_tracks):
            uri = f"spotify:track:{track_id}"
            response = make_spotify_request(
                "POST",
                "/me/player/queue",
                params={"uri": uri}
            )
            
            if response.get("success"):
                added_count += 1
            else:
                error = response.get("error", "Unknown error")
                if response.get("status") == 404:
                    return "⚠️ No active Spotify device found. Please open Spotify on a device and try again."
                queue_errors.append(f"{track_info}: {error}")
        
        result = f"✅ Added {added_count} track(s) to queue:\n\n" + "\n".join(found_tracks[:added_count])
        
        if failed_searches:
            result += f"\n\n⚠️ Failed to find {len(failed_searches)} track(s):\n" + "\n".join(failed_searches)
        
        if queue_errors:
            result += f"\n\n❌ Failed to queue {len(queue_errors)} track(s):\n" + "\n".join(queue_errors)
        
        return result
    
    else:
        # Single track by ID
        uri = f"spotify:track:{spotify_id}"
        
        response = make_spotify_request(
            "POST",
            "/me/player/queue",
            params={"uri": uri}
        )
        
        if response.get("success"):
            return f"✅ Added track to queue: {spotify_id}"
        else:
            error = response.get("error", "Unknown error")
            if response.get("status") == 404:
                return "⚠️ No active Spotify device found. Please open Spotify on a device and try again."
            return f"❌ Failed to add to queue: {error}"


# =============================================================================
# BATCH OPERATIONS
# =============================================================================

def _execute_batch(operations: List[Dict[str, Any]]) -> str:
    """
    Execute multiple Spotify operations in a single tool call!
    MASSIVE API credit saver - combines multiple actions into ONE call.
    
    Args:
        operations: List of operation dictionaries, each containing:
                   - action: The action to perform (any valid spotify_control action EXCEPT execute_batch)
                   - All other parameters for that specific action
    
    Returns:
        Combined results from all operations with individual success/error reporting
    """
    if not operations or not isinstance(operations, list):
        return "❌ operations must be a non-empty list"
    
    if len(operations) > 10:
        return "❌ Maximum 10 operations per batch call (to prevent timeouts)"
    
    results = []
    success_count = 0
    error_count = 0
    
    for idx, op in enumerate(operations, 1):
        if not isinstance(op, dict):
            results.append(f"❌ Operation {idx}: Invalid format (must be a dictionary)")
            error_count += 1
            continue
        
        operation_action = op.get("action")
        if not operation_action:
            results.append(f"❌ Operation {idx}: Missing 'action' parameter")
            error_count += 1
            continue
        
        if operation_action == "execute_batch":
            results.append(f"❌ Operation {idx}: Cannot nest execute_batch calls")
            error_count += 1
            continue
        
        # Execute the operation
        try:
            # Extract parameters for this operation
            query = op.get("query")
            spotify_id = op.get("spotify_id")
            content_type = op.get("content_type")
            playlist_name = op.get("playlist_name")
            playlist_description = op.get("playlist_description")
            track_ids = op.get("track_ids")
            songs = op.get("songs")
            limit = op.get("limit")
            
            # Call the appropriate function based on action
            if operation_action == "search":
                if not query:
                    result = "❌ Query required for search"
                else:
                    content_type = content_type or "track"
                    limit = limit or 10
                    result = search_spotify(query, content_type, limit)
            
            elif operation_action == "play":
                if not spotify_id and not query:
                    result = "❌ Either spotify_id or query required to play music"
                else:
                    content_type = content_type or "track"
                    result = play_music(spotify_id=spotify_id, content_type=content_type, query=query)
            
            elif operation_action == "pause":
                result = pause_playback()
            
            elif operation_action == "next":
                result = skip_to_next()
            
            elif operation_action == "previous":
                result = skip_to_previous()
            
            elif operation_action == "now_playing":
                result = get_now_playing()
            
            elif operation_action == "create_playlist":
                if not playlist_name:
                    result = "❌ playlist_name required to create playlist"
                else:
                    # If songs provided, create and populate in one go!
                    if songs:
                        result = create_and_populate_playlist(
                            name=playlist_name,
                            songs=songs,
                            description=playlist_description or "",
                            public=False
                        )
                    else:
                        result = create_playlist(playlist_name, playlist_description or "")
            
            elif operation_action == "add_to_playlist":
                if not spotify_id:
                    result = "❌ spotify_id (playlist ID) required"
                elif not track_ids and not query:
                    result = "❌ Either track_ids or query required"
                else:
                    # Convert comma-separated track_ids to list if provided
                    track_list = None
                    if track_ids:
                        track_list = [tid.strip() for tid in track_ids.split(",")]
                    result = add_tracks_to_playlist(playlist_id=spotify_id, track_ids=track_list, query=query)
            
            elif operation_action == "my_playlists":
                limit = limit or 20
                result = get_my_playlists(limit)
            
            elif operation_action == "add_to_queue":
                if not spotify_id and not query:
                    result = "❌ Either spotify_id or query required to add to queue"
                else:
                    content_type = content_type or "track"
                    result = add_to_queue(spotify_id=spotify_id, content_type=content_type, query=query)
            
            else:
                result = f"❌ Unknown action: {operation_action}"
            
            # Check if operation succeeded or failed
            if result.startswith("❌"):
                error_count += 1
            else:
                success_count += 1
            
            results.append(f"🎵 Operation {idx} ({operation_action}):\n{result}")
        
        except Exception as e:
            results.append(f"❌ Operation {idx} ({operation_action}): Error - {str(e)}")
            error_count += 1
    
    # Build summary
    summary = f"📊 Batch Results: {success_count} succeeded, {error_count} failed\n"
    summary += "=" * 60 + "\n\n"
    summary += "\n\n".join(results)
    
    return summary


# =============================================================================
# MAIN TOOL FUNCTION
# =============================================================================

def spotify_control(
    action: str,
    query: Optional[str] = None,
    spotify_id: Optional[str] = None,
    content_type: Optional[str] = None,
    playlist_name: Optional[str] = None,
    playlist_description: Optional[str] = None,
    track_ids: Optional[str] = None,
    songs: Optional[str] = None,
    limit: Optional[int] = None,
    operations: Optional[List[Dict[str, Any]]] = None
) -> str:
    """
    Control Spotify playback and manage playlists
    
    Args:
        action: Action to perform (search, play, pause, next, previous, now_playing, 
                create_playlist, add_to_playlist, add_to_queue, my_playlists, execute_batch)
        query: Search query - can be used with 'search', 'play', 'add_to_playlist', 'add_to_queue'
               For multiple tracks, separate queries with semicolons: "track1; track2; track3"
        spotify_id: Spotify ID of content to play or playlist to modify
        content_type: Type of content (track, artist, album, playlist)
        playlist_name: Name for new playlist
        playlist_description: Description for new playlist
        track_ids: Comma-separated list of track IDs (for add_to_playlist)
        songs: Semicolon-separated song queries (for create_playlist with songs)
               You can add AS MANY songs as you want - no limit!
               Example: "bohemian rhapsody; stairway to heaven; hotel california; ..."
        limit: Limit for search/list results
        operations: List of operation dicts (ONLY for 'execute_batch' action)
                   Each operation is a dict with 'action' and its required parameters
                   Example: [{"action": "create_playlist", "playlist_name": "Mix", "songs": "..."},
                            {"action": "play", "query": "Mix", "content_type": "playlist"}]
    
    Returns:
        Result message
    """
    try:
        if action == "search":
            if not query:
                return "❌ Query required for search"
            content_type = content_type or "track"
            limit = limit or 10
            return search_spotify(query, content_type, limit)
        
        elif action == "play":
            if not spotify_id and not query:
                return "❌ Either spotify_id or query required to play music"
            content_type = content_type or "track"
            return play_music(spotify_id=spotify_id, content_type=content_type, query=query)
        
        elif action == "pause":
            return pause_playback()
        
        elif action == "next":
            return skip_to_next()
        
        elif action == "previous":
            return skip_to_previous()
        
        elif action == "now_playing":
            return get_now_playing()
        
        elif action == "create_playlist":
            if not playlist_name:
                return "❌ playlist_name required to create playlist"
            
            # If songs provided, create and populate in one go!
            if songs:
                return create_and_populate_playlist(
                    name=playlist_name,
                    songs=songs,
                    description=playlist_description or "",
                    public=False
                )
            # Otherwise create empty playlist (rare but possible)
            else:
                return create_playlist(playlist_name, playlist_description or "")
        
        elif action == "add_to_playlist":
            if not spotify_id:
                return "❌ spotify_id (playlist ID) required"
            if not track_ids and not query:
                return "❌ Either track_ids or query required"
            
            # Convert comma-separated track_ids to list if provided
            track_list = None
            if track_ids:
                track_list = [tid.strip() for tid in track_ids.split(",")]
            
            return add_tracks_to_playlist(playlist_id=spotify_id, track_ids=track_list, query=query)
        
        elif action == "my_playlists":
            limit = limit or 20
            return get_my_playlists(limit)
        
        elif action == "add_to_queue":
            if not spotify_id and not query:
                return "❌ Either spotify_id or query required to add to queue"
            content_type = content_type or "track"
            return add_to_queue(spotify_id=spotify_id, content_type=content_type, query=query)
        
        elif action == "execute_batch":
            if not operations:
                return "❌ operations list required for execute_batch action"
            return _execute_batch(operations)
        
        else:
            return f"❌ Unknown action: {action}. Valid actions: search, play, pause, next, previous, now_playing, create_playlist, add_to_playlist, add_to_queue, my_playlists, execute_batch"
    
    except Exception as e:
        return f"❌ Error: {str(e)}"


# =============================================================================
# MAIN - FOR TESTING
# =============================================================================

if __name__ == "__main__":
    # Test: Get now playing
    print(spotify_control(action="now_playing"))
    print("\n" + "="*60 + "\n")
    
    # Test: Search
    print(spotify_control(action="search", query="bohemian rhapsody", content_type="track", limit=5))
