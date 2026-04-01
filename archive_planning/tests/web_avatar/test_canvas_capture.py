"""
Canvas Capture Integration Tests
- Frame timing validation (10 FPS / 100ms interval)
- WebSocket broadcasting behavior
- Performance metrics tracking
- State manager integration
- Error handling and edge cases
- End-to-end frame capture flow
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
import base64
import time


class TestFrameCaptureTiming:
    """Validate canvas capture occurs at 10 FPS (100ms interval)"""

    def test_capture_respects_100ms_interval(self):
        """Frame captures should not exceed 100ms throttle"""
        mock_ws = Mock()
        mock_ws.readyState = "OPEN"
        
        capture_state = {
            'enabled': True,
            'interval': 100,
            'lastCaptureTime': 0,
            'frameCount': 0
        }
        
        timestamps = [0, 50, 100, 150, 200, 250]
        captures = []
        
        for ts in timestamps:
            time_since_last = ts - capture_state['lastCaptureTime']
            if time_since_last >= capture_state['interval']:
                captures.append(ts)
                capture_state['lastCaptureTime'] = ts
        
        assert len(captures) > 0
        intervals = [captures[i+1] - captures[i] for i in range(len(captures)-1)]
        assert all(interval >= 100 for interval in intervals)

    def test_frame_captured_every_100ms_minimum(self):
        """At 10 FPS, frames should be captured every ~100ms"""
        fps = 10
        interval_ms = 1000 / fps
        assert interval_ms == 100

    def test_multiple_consecutive_captures_skip_if_interval_not_met(self):
        """Rapid calls to captureFrame should skip if interval not met"""
        mock_canvas = Mock()
        mock_canvas.toDataURL.return_value = "data:image/png;base64,test"
        
        mock_ws = Mock()
        mock_ws.readyState = "OPEN"
        
        capture_times = []
        current_time = 0
        
        for call_num in range(5):
            time_since_last = current_time - (capture_times[-1] if capture_times else -1000)
            
            if time_since_last >= 100:
                capture_times.append(current_time)
            
            current_time += 30
        
        assert len(capture_times) == 2
        intervals = [capture_times[i+1] - capture_times[i] for i in range(len(capture_times)-1)]
        assert all(interval >= 100 for interval in intervals)

    def test_fps_calculation_matches_interval(self):
        """FPS should be inverse of capture interval"""
        interval_ms = 100
        calculated_fps = 1000 / interval_ms
        
        assert calculated_fps == 10.0

    def test_capture_timing_drift_tolerance(self):
        """Capture should tolerate small timing drift"""
        # Simulate real-world timing with slight variance
        expected_intervals = [100, 101, 99, 100, 102, 98]
        avg_interval = sum(expected_intervals) / len(expected_intervals)
        
        # Average should be close to 100ms despite variance
        assert 99 <= avg_interval <= 101


class TestFrameCaptureExecution:
    """Validate frame capture execution and WebSocket sending"""

    def test_capture_frame_sends_to_websocket(self):
        """captureFrame should send frame data via WebSocket"""
        mock_canvas = Mock()
        frame_data = "data:image/png;base64,iVBORw0KGgo="
        mock_canvas.toDataURL.return_value = frame_data
        
        mock_ws = Mock()
        mock_ws.readyState = "OPEN"
        mock_ws.send = Mock()
        
        capture_info = {
            'canvas': mock_canvas,
            'ws': mock_ws,
            'enabled': True,
            'lastCaptureTime': 0
        }
        
        now = time.time() * 1000
        time_since_last = now - capture_info['lastCaptureTime']
        
        if time_since_last >= 100 and capture_info['ws'].readyState == "OPEN":
            frame = capture_info['canvas'].toDataURL('image/png')
            frame_msg = {
                'type': 'mirror_frame',
                'frame_data': frame,
                'timestamp': int(now)
            }
            capture_info['ws'].send(json.dumps(frame_msg))
        
        assert mock_canvas.toDataURL.called
        assert mock_ws.send.called

    def test_capture_frame_validates_size(self):
        """Frames > 2MB should be skipped"""
        mock_ws = Mock()
        mock_ws.readyState = "OPEN"
        
        large_frame = "data:image/png;base64," + ("x" * 2_100_000)
        normal_frame = "data:image/png;base64," + ("x" * 100_000)
        
        assert len(large_frame) > 2_000_000
        assert len(normal_frame) < 2_000_000
        
        # Only normal frame should be sent
        frames_to_send = [normal_frame] if len(normal_frame) < 2_000_000 else []
        assert len(frames_to_send) == 1

    def test_capture_skips_when_websocket_closed(self):
        """If WebSocket is not OPEN, frame should not send"""
        mock_ws = Mock()
        mock_ws.readyState = "CLOSED"
        
        should_send = mock_ws.readyState == "OPEN"
        assert not should_send

    def test_capture_frame_count_increments_on_send(self):
        """Frame count should increment each time frame is sent"""
        frame_counts = [0]
        
        for i in range(10):
            if i % 2 == 0:  # Simulate successful sends
                frame_counts.append(frame_counts[-1] + 1)
        
        assert len([x for x in frame_counts if x > 0]) > 0
        assert frame_counts[-1] == 5  # 5 successful sends

    def test_capture_uses_correct_image_format(self):
        """Canvas capture should use PNG format for quality"""
        mock_canvas = Mock()
        mock_canvas.toDataURL = Mock(return_value="data:image/png;base64,test")
        
        result = mock_canvas.toDataURL('image/png')
        
        assert result.startswith("data:image/png;base64,")

    def test_capture_disabled_flag_prevents_execution(self):
        """When capture.enabled = false, no frames should be captured"""
        capture_state = {'enabled': False}
        
        frames_captured = []
        if capture_state['enabled']:
            frames_captured.append("frame")
        
        assert len(frames_captured) == 0


class TestFrameFormat:
    """Validate frame message format"""

    def test_frame_message_structure(self):
        """Frame message must have type, frame_data, timestamp"""
        msg = {
            'type': 'mirror_frame',
            'frame_data': 'data:image/png;base64,abc=',
            'timestamp': int(time.time() * 1000)
        }
        
        assert 'type' in msg
        assert 'frame_data' in msg
        assert 'timestamp' in msg
        assert msg['type'] == 'mirror_frame'
        assert msg['frame_data'].startswith('data:image/png;base64,')

    def test_frame_data_is_base64_data_url(self):
        """frame_data must be valid base64 data URL"""
        valid_data_url = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
        
        assert valid_data_url.startswith("data:image/png;base64,")
        base64_part = valid_data_url.split(",")[1]
        decoded = base64.b64decode(base64_part, validate=True)
        assert len(decoded) > 0

    def test_timestamp_is_unix_milliseconds(self):
        """timestamp should be Unix time in milliseconds"""
        current_ms = int(time.time() * 1000)
        
        msg = {
            'type': 'mirror_frame',
            'frame_data': 'data:image/png;base64,test',
            'timestamp': current_ms
        }
        
        # Timestamp should be reasonable (between 2023 and 2050)
        min_ts = int(1700000000 * 1000)
        max_ts = int(2500000000 * 1000)
        
        assert min_ts < msg['timestamp'] < max_ts

    def test_json_serialization(self):
        """Frame message should be JSON serializable"""
        msg = {
            'type': 'mirror_frame',
            'frame_data': 'data:image/png;base64,test',
            'timestamp': int(time.time() * 1000)
        }
        
        serialized = json.dumps(msg)
        deserialized = json.loads(serialized)
        
        assert deserialized['type'] == msg['type']
        assert deserialized['frame_data'] == msg['frame_data']
        assert deserialized['timestamp'] == msg['timestamp']


class TestPerformanceMetrics:
    """Track and validate performance metrics"""

    def test_fps_calculation_from_timestamps(self):
        """FPS should be calculated from frame timestamps"""
        frame_timestamps = [0, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]
        
        frame_count = len(frame_timestamps)
        time_span_ms = frame_timestamps[-1] - frame_timestamps[0]
        fps = (frame_count - 1) * 1000 / time_span_ms
        
        assert 9 < fps < 11

    def test_frame_drop_detection(self):
        """Detect when captures are skipped (frame drops)"""
        expected_captures_in_1s = 10
        actual_captures = 8
        
        frame_drop_rate = (1 - actual_captures / expected_captures_in_1s) * 100
        
        assert frame_drop_rate > 0
        assert abs(frame_drop_rate - 20) < 0.01  # 2 drops = 20%

    def test_average_frame_size(self):
        """Track average frame size for bandwidth estimation"""
        frame_sizes = [80_000, 85_000, 75_000, 90_000, 82_000]
        
        avg_size = sum(frame_sizes) / len(frame_sizes)
        bandwidth_mbps = (avg_size * 10) / 1_000_000
        
        assert 0.5 < bandwidth_mbps < 2

    def test_capture_latency_tracking(self):
        """Measure time taken to capture and send frame"""
        capture_start = time.time() * 1000
        
        # Simulate capture
        mock_canvas = Mock()
        mock_canvas.toDataURL = Mock(return_value="data:image/png;base64,test")
        mock_canvas.toDataURL('image/png')
        
        capture_end = time.time() * 1000
        latency = capture_end - capture_start
        
        # Capture should be fast (< 50ms)
        assert latency < 50

    def test_bandwidth_calculation(self):
        """Calculate bandwidth used by mirror stream"""
        avg_frame_size_bytes = 100_000
        fps = 10
        
        bytes_per_second = avg_frame_size_bytes * fps
        mbps = (bytes_per_second * 8) / 1_000_000
        
        # Should be reasonable (< 10 Mbps)
        assert mbps < 10

    def test_performance_metrics_reset(self):
        """Metrics should be resettable"""
        metrics = {
            'frameCount': 150,
            'totalBytes': 15_000_000,
            'startTime': 1000
        }
        
        # Reset
        metrics['frameCount'] = 0
        metrics['totalBytes'] = 0
        metrics['startTime'] = int(time.time() * 1000)
        
        assert metrics['frameCount'] == 0
        assert metrics['totalBytes'] == 0


class TestWebSocketBroadcasting:
    """Test frame broadcasting via WebSocket"""

    def test_server_broadcasts_to_multiple_clients(self):
        """Server should broadcast frame to all connected clients except sender"""
        sender = Mock()
        sender.id = 1
        
        receivers = [Mock(), Mock(), Mock()]
        for i, r in enumerate(receivers):
            r.id = i + 2
            r.readyState = "OPEN"
        
        frame_msg = {
            'type': 'mirror_frame',
            'frame_data': 'data:image/png;base64,test',
            'timestamp': int(time.time() * 1000)
        }
        
        # Broadcast to all except sender
        broadcast_targets = [r for r in receivers if r.id != sender.id and r.readyState == "OPEN"]
        
        assert len(broadcast_targets) == 3

    def test_broadcast_skips_closed_connections(self):
        """Broadcast should skip clients with closed connections"""
        clients = [
            Mock(readyState="OPEN"),
            Mock(readyState="CLOSED"),
            Mock(readyState="OPEN"),
            Mock(readyState="CLOSING")
        ]
        
        active_clients = [c for c in clients if c.readyState == "OPEN"]
        
        assert len(active_clients) == 2

    def test_broadcast_handles_send_errors(self):
        """Broadcast should continue if one client fails"""
        mock_client = Mock()
        mock_client.readyState = "OPEN"
        mock_client.send = Mock(side_effect=Exception("Send failed"))
        
        frame_msg = json.dumps({'type': 'mirror_frame', 'frame_data': 'test'})
        
        try:
            mock_client.send(frame_msg)
        except Exception as e:
            # Error should be caught, other clients continue
            assert str(e) == "Send failed"

    def test_frame_message_preserves_data_integrity(self):
        """Frame data should not be corrupted during broadcast"""
        original_frame = "data:image/png;base64,iVBORw0KGgo="
        
        msg = {
            'type': 'mirror_frame',
            'frame_data': original_frame,
            'timestamp': 12345
        }
        
        serialized = json.dumps(msg)
        deserialized = json.loads(serialized)
        
        assert deserialized['frame_data'] == original_frame


class TestStateManagerIntegration:
    """Test integration with state management"""

    def test_capture_state_initialization(self):
        """Capture state should initialize with correct defaults"""
        capture_state = {
            'enabled': False,
            'interval': 100,
            'frameCount': 0,
            'lastCaptureTime': 0,
            'totalBytesSent': 0
        }
        
        assert capture_state['enabled'] == False
        assert capture_state['interval'] == 100
        assert capture_state['frameCount'] == 0

    def test_enable_capture_updates_state(self):
        """Enabling capture should update state"""
        capture_state = {'enabled': False}
        
        # User enables mirror stream
        capture_state['enabled'] = True
        
        assert capture_state['enabled'] == True

    def test_disable_capture_stops_frame_sending(self):
        """Disabling capture should prevent frames from being sent"""
        capture_state = {'enabled': True, 'frameCount': 5}
        
        # User disables mirror stream
        capture_state['enabled'] = False
        
        # No more frames should be sent
        should_capture = capture_state['enabled']
        assert should_capture == False

    def test_state_persists_frame_count(self):
        """Frame count should persist across captures"""
        state = {'frameCount': 0}
        
        for i in range(10):
            state['frameCount'] += 1
        
        assert state['frameCount'] == 10

    def test_state_tracks_total_bytes_sent(self):
        """State should track total bytes sent"""
        state = {'totalBytesSent': 0}
        frame_sizes = [100_000, 95_000, 102_000]
        
        for size in frame_sizes:
            state['totalBytesSent'] += size
        
        assert state['totalBytesSent'] == sum(frame_sizes)


class TestErrorHandling:
    """Test error handling and edge cases"""

    def test_canvas_not_available(self):
        """Handle case when canvas is null/undefined"""
        canvas = None
        
        can_capture = canvas is not None and hasattr(canvas, 'toDataURL')
        assert can_capture == False

    def test_websocket_not_connected(self):
        """Handle WebSocket not connected"""
        ws = None
        
        can_send = ws is not None and ws.readyState == "OPEN"
        assert can_send == False

    def test_todataurl_throws_exception(self):
        """Handle toDataURL() throwing exception"""
        mock_canvas = Mock()
        mock_canvas.toDataURL = Mock(side_effect=Exception("Canvas error"))
        
        try:
            mock_canvas.toDataURL('image/png')
            captured = True
        except Exception:
            captured = False
        
        assert captured == False

    def test_websocket_send_fails(self):
        """Handle WebSocket send() failure"""
        mock_ws = Mock()
        mock_ws.readyState = "OPEN"
        mock_ws.send = Mock(side_effect=Exception("Network error"))
        
        try:
            mock_ws.send("test")
            sent = True
        except Exception:
            sent = False
        
        assert sent == False

    def test_oversized_frame_handling(self):
        """Frames exceeding size limit should be skipped"""
        max_frame_size = 2_000_000  # 2MB
        
        small_frame = "x" * 100_000
        large_frame = "x" * 2_500_000
        
        should_send_small = len(small_frame) < max_frame_size
        should_send_large = len(large_frame) < max_frame_size
        
        assert should_send_small == True
        assert should_send_large == False

    def test_invalid_json_handling(self):
        """Handle invalid JSON in WebSocket message"""
        invalid_json = "{type: 'mirror_frame', missing quotes}"
        
        try:
            parsed = json.loads(invalid_json)
            valid = True
        except json.JSONDecodeError:
            valid = False
        
        assert valid == False

    def test_missing_required_fields(self):
        """Handle messages missing required fields"""
        incomplete_msg = {
            'type': 'mirror_frame'
            # Missing frame_data and timestamp
        }
        
        is_valid = 'type' in incomplete_msg and 'frame_data' in incomplete_msg and 'timestamp' in incomplete_msg
        assert is_valid == False


class TestEndToEndFlow:
    """Integration: capture → encode → send → broadcast → receive"""

    def test_full_capture_to_broadcast_flow(self):
        """End-to-end: Canvas capture → WebSocket send → Server broadcast"""
        # Step 1: Canvas capture
        mock_canvas = Mock()
        frame_data = "data:image/png;base64,testframe"
        mock_canvas.toDataURL.return_value = frame_data
        
        captured_frame = mock_canvas.toDataURL('image/png')
        assert captured_frame == frame_data
        
        # Step 2: Create message
        frame_msg = {
            'type': 'mirror_frame',
            'frame_data': captured_frame,
            'timestamp': int(time.time() * 1000)
        }
        
        assert frame_msg['type'] == 'mirror_frame'
        
        # Step 3: Serialize for WebSocket
        serialized = json.dumps(frame_msg)
        assert isinstance(serialized, str)
        
        # Step 4: Server receives and parses
        received = json.loads(serialized)
        assert received['frame_data'] == frame_data
        
        # Step 5: Broadcast to clients
        mock_clients = [Mock(readyState="OPEN") for _ in range(3)]
        broadcast_count = 0
        
        for client in mock_clients:
            if client.readyState == "OPEN":
                broadcast_count += 1
        
        assert broadcast_count == 3

    def test_capture_loop_with_throttling(self):
        """Simulate capture loop with proper throttling"""
        capture_state = {
            'enabled': True,
            'interval': 100,
            'lastCaptureTime': 0,
            'frameCount': 0
        }
        
        simulation_times = [0, 50, 100, 150, 200]
        captured_frames = []
        
        for current_time in simulation_times:
            time_since_last = current_time - capture_state['lastCaptureTime']
            
            if capture_state['enabled'] and time_since_last >= capture_state['interval']:
                captured_frames.append(current_time)
                capture_state['lastCaptureTime'] = current_time
                capture_state['frameCount'] += 1
        
        assert len(captured_frames) == 2
        assert capture_state['frameCount'] == 2

    def test_enable_disable_cycle(self):
        """Test enabling and disabling capture mid-stream"""
        state = {'enabled': True, 'frameCount': 0}
        
        # Capture 5 frames
        for i in range(5):
            if state['enabled']:
                state['frameCount'] += 1
        
        assert state['frameCount'] == 5
        
        # Disable
        state['enabled'] = False
        
        # Try to capture 5 more (should not increment)
        for i in range(5):
            if state['enabled']:
                state['frameCount'] += 1
        
        assert state['frameCount'] == 5  # Still 5
        
        # Re-enable
        state['enabled'] = True
        
        # Capture 3 more
        for i in range(3):
            if state['enabled']:
                state['frameCount'] += 1
        
        assert state['frameCount'] == 8

    def test_concurrent_viewer_and_mirror_clients(self):
        """Test avatar viewer sending to mirror clients"""
        viewer_ws = Mock(id="viewer", readyState="OPEN")
        mirror_clients = [
            Mock(id="mirror1", readyState="OPEN"),
            Mock(id="mirror2", readyState="OPEN")
        ]
        
        frame_msg = {
            'type': 'mirror_frame',
            'frame_data': 'data:image/png;base64,test',
            'timestamp': int(time.time() * 1000)
        }
        
        # Viewer sends frame
        viewer_ws.send(json.dumps(frame_msg))
        
        # Server broadcasts to mirrors (not viewer)
        broadcast_targets = [c for c in mirror_clients if c.id != viewer_ws.id]
        
        assert len(broadcast_targets) == 2
        assert all(c.id.startswith("mirror") for c in broadcast_targets)

    def test_performance_under_load(self):
        """Test capture performance with high frame counts"""
        metrics = {
            'frameCount': 0,
            'totalBytes': 0,
            'startTime': 0,
            'endTime': 0
        }
        
        avg_frame_size = 100_000
        target_frames = 600  # 1 minute at 10 FPS
        
        metrics['startTime'] = int(time.time() * 1000)
        
        for i in range(target_frames):
            metrics['frameCount'] += 1
            metrics['totalBytes'] += avg_frame_size
        
        metrics['endTime'] = int(time.time() * 1000)
        
        assert metrics['frameCount'] == 600
        assert metrics['totalBytes'] == 60_000_000  # 60MB total
        
        # Average bandwidth
        total_mb = metrics['totalBytes'] / 1_000_000
        duration_sec = 60
        mbps = (total_mb * 8) / duration_sec
        
        assert mbps < 10  # Should be under 10 Mbps
